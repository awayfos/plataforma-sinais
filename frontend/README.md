# Frontend — Plataforma Sinais

Next.js 16 (App Router) + React 19 + TypeScript estrito + Tailwind CSS v4 + TradingView Lightweight Charts 5.
Toda a interface em português do Brasil. O frontend só fala com `/api` (contrato em `docs/api/contrato-v1.md`).

## Rodar localmente

Requer Node.js ≥ 20.9 (o CI usa Node 22) e o backend FastAPI rodando em `http://127.0.0.1:8000`.

```bash
cd frontend
npm ci               # requer acesso ao registro npm (ver "Lockfile" abaixo)
npm run dev          # http://localhost:3000
```

O Next repassa `/api/*` para o backend por um rewrite (`next.config.ts`). Para outro endereço:

```bash
SINAIS_API_URL=http://10.0.0.5:8000 npm run dev
```

`SINAIS_API_URL` é lido quando o servidor monta as rotas: em produção, defina-o **no build** (`npm run build`).

O WebSocket usa `ws(s)://<mesmo host>/api/ws`, também repassado pelo rewrite. Se o proxy à frente não repassar
upgrades de WebSocket, aponte direto para o backend com `NEXT_PUBLIC_WS_URL=ws://127.0.0.1:8000/api/ws`
(variável pública, lida no build; não é segredo).

Cookies: o backend define `sinais_sessao` (httpOnly, Secure) e `sinais_csrf`. Navegadores aceitam cookies `Secure`
em `http://localhost`; use `localhost` (não o IP da máquina) no desenvolvimento.

## Scripts

| Comando | O que faz |
|---|---|
| `npm run dev` | servidor de desenvolvimento |
| `npm run lint` | ESLint 9 (`eslint-config-next` core-web-vitals + typescript) |
| `npm run typecheck` | `next typegen` + `tsc --noEmit` |
| `npm test` | Vitest + Testing Library (jsdom) |
| `npm run build` / `npm start` | build e servidor de produção |
| `npm run e2e` | Playwright contra `next start` na porta 3100 (rode `npm run build` antes) |

Os testes ponta a ponta simulam a API (`page.route`) e o WebSocket (`page.routeWebSocket`) em `e2e/mocks.ts`.
Esses dados são **simulações de teste**, rotulados como tal, e nunca aparecem na aplicação.

## Lockfile

O `package-lock.json` foi gerado no CI (o ambiente em que o frontend foi escrito não tem acesso ao registro npm)
e o CI instala com `npm ci`. Para atualizar dependências, rode `npm install` numa máquina com rede e faça commit
do lock. O `.npmrc` usa `legacy-peer-deps=true` porque o npm 10 ainda quebra ao resolver os peers opcionais
vitest → jsdom → `@napi-rs/canvas` (`Cannot read properties of null (reading 'edgesOut')`), conferido em
2026-11-26; todos os peers necessários estão declarados.

## Estrutura

```
src/
  proxy.ts                 # só confere se o cookie de sessão existe (Next 16: antigo middleware)
  app/
    login/ assinatura/     # públicas
    (app)/                 # cabeçalho, sessão, WebSocket e aviso de risco
      terminal/ historico/ perfil/
      admin/{usuarios,planos,assinaturas,acessos,auditoria,payout,qualidade}
  components/
    terminal/              # Grafico, PainelAnalise, TabelaSinais, CartaoSinal, BarraFerramentas…
    admin/ auth/ perfil/ historico/ sessao/ ui/
  lib/
    api/                   # tipos do contrato, cliente HTTP (CSRF, 401/402/429), endpoints
    ws/                    # cliente WebSocket tipado com reconexão e provedor React
    indicadores.ts         # EMA, SMA, Bollinger, VWAP, RSI, MACD (só para o gráfico)
    formato.ts sinais.ts glossario.ts
tests/                     # Vitest
e2e/                       # Playwright
```

## Decisões

- **Autoridade no servidor.** O `proxy.ts` não valida nada além da existência do cookie. Qualquer `401` leva ao
  login, `402` à tela de assinatura, `429` mostra "Muitas requisições…". O WebSocket fechado com `4401`/`4402`
  não reconecta. Depois de 3 quedas seguidas (um handshake recusado chega como 1006), o frontend confere a
  sessão com `GET /api/eu`, e os tratadores de 401/402 redirecionam. Ao reconectar, candles, análise e sinais
  são recarregados por REST; enquanto não há tempo real, sinais e análise ficam esmaecidos e marcados como
  possivelmente desatualizados.
- **Preços como string.** Preços da API são exibidos a partir da string decimal, sem passar por `float`. Só o
  gráfico converte para número.
- **Horário de Brasília.** Tudo trafega em ms UTC; a tela e o eixo intradiário do gráfico mostram UTC−3 (o
  Brasil não tem horário de verão desde 2019). Barras de 1d e 1w ficam na data UTC de abertura, sem deslocamento.
- **Relógio do servidor.** A contagem da janela de entrada usa a hora do servidor estimada pelo cabeçalho `Date`
  das respostas, com 1 s de margem de segurança, e não o relógio da máquina.
- **VWAP** é ancorado em 00:00 UTC (21:00 em Brasília) e só fica disponível em tempos intradiários.
- **Indicadores do gráfico** são calculados no navegador a partir dos candles exibidos, só para visualização. A
  análise oficial (`/api/analise`) vem do backend.
- **Nenhum dado inventado.** Probabilidade só aparece quando o backend envia, sempre com `n`. Campos fora do
  contrato (tolerância de preço, preço de referência do sinal) só aparecem se vierem na resposta.
