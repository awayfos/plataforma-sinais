# Fase 9 (+ UI da Fase 10) — Plataforma web: Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir o frontend (terminal de análise, sinais por expiração, histórico, perfil e painel admin) contra o contrato `docs/api/contrato-v1.md`, escuro, rápido e honesto (nenhum dado falso).

**Architecture:** Next.js 16 (App Router) com páginas cliente que falam só com `/api` (rewrite para o FastAPI em `http://127.0.0.1:8000`). `src/proxy.ts` só confere se o cookie `sinais_sessao` existe; o backend é a autoridade (401 → `/login`, 402 → `/assinatura`). Camada `src/lib/api` (tipos do contrato, cliente HTTP com CSRF, endpoints), `src/lib/ws` (cliente WebSocket tipado com reconexão), `src/lib/indicadores` (funções puras para sobreposições do gráfico), componentes por área (`terminal/`, `admin/`, `ui/`).

**Tech Stack:** Next.js 16, React 19, TypeScript strict, Tailwind CSS v4 (`@tailwindcss/postcss`), lightweight-charts 5, Vitest + Testing Library (jsdom), Playwright (mocks de rota e de WebSocket), ESLint 9 + `eslint-config-next` 16.

**Spec:** `docs/superpowers/specs/2026-11-25-plataforma-sinais-design.md` (§5, §6, §10, §12.6, §15) e `docs/api/contrato-v1.md`.

## Global Constraints

- Toda a interface em português do Brasil. Horários exibidos em `America/Sao_Paulo`; dados trafegam em ms UTC.
- Preços chegam como string decimal: exibir a string (sem arredondar com float); converter para `number` só no gráfico.
- Mutações (`POST`, `PUT`, `PATCH`, `DELETE`) enviam `X-CSRF-Token` = valor do cookie `sinais_csrf`. `credentials: "same-origin"`.
- Erros `{"erro": {"codigo", "mensagem"}}`: `401` → `/login?proximo=<rota>` (exceto na própria chamada de login), `402` → `/assinatura`, `429` → "Muitas requisições. Aguarde alguns segundos e tente de novo."
- WebSocket `/api/ws`: `{"acao":"assinar"|"cancelar","canal"}`; recebe `{"canal","dados"}`. Fecho `4401` → login, `4402` → `/assinatura`, sem reconectar. Outros fechos: reconexão com backoff exponencial com jitter, 0,5 s a 30 s, e reassinatura de todos os canais.
- Sinais: expirações `1m, 5m, 15m, 30m, 60m` (rótulos "1 min", "5 min", "15 min", "30 min", "1 h"). AGUARDAR mostra o `motivo`. Probabilidade só quando não nula, sempre com `n`.
- Aviso de risco permanente em todas as telas logadas.
- Nenhum dado simulado fora de testes; mocks de teste ficam em `tests/` e `e2e/` e são rotulados como tal.
- Sem segredos no frontend. Única variável: `SINAIS_API_URL` (servidor Next, rewrite) e `NEXT_PUBLIC_WS_URL` (opcional).
- Rede indisponível no ambiente local: sem lockfile; o CI (GitHub Actions) instala e roda lint, tipos, Vitest, build e Playwright.

## Review Focus

1. Sinal cuja `janela_ate` já passou (ou passa com a tela aberta): o cartão vira "Fora da janela, não entre" sem recarregar. Teste em Task 5.
2. Queda do WebSocket durante a sessão: reconecta com atraso crescente e reassina os canais; fecho 4402 nunca reconecta. Teste em Task 2.
3. Resposta de erro sem corpo JSON (proxy 502, HTML): mensagem genérica, sem exceção opaca. Teste em Task 2.
4. Candle ao vivo de outro tempo gráfico ou de um ativo antigo após a troca: ignorado (o canal é cancelado e a mensagem filtrada pelo canal atual). Teste em Task 4.
5. Lista de sinais incompleta ou fora de ordem: a tabela sempre mostra as 5 expirações em ordem, com "Sem dados" na que faltar. Teste em Task 5.

---

### Task 1: Esqueleto, CI e design system

**Files:** `frontend/{package.json,tsconfig.json,next.config.ts,postcss.config.mjs,eslint.config.mjs,vitest.config.ts,vitest.setup.ts,playwright.config.ts,.gitignore,README.md}`, `frontend/src/app/{layout.tsx,globals.css,page.tsx}`, `frontend/src/proxy.ts`, `frontend/src/components/ui/*`, `.github/workflows/frontend.yml`. Tests: `frontend/tests/proxy.test.ts`, `frontend/tests/ui/dica.test.tsx`.

**Interfaces — Produces:** `proxy(request: NextRequest): NextResponse` (rotas públicas: `/login`, `/assinatura`, `/_next`, `/api`, arquivos estáticos); `Dica({termo}: {termo: TermoGlossario})` botão "aprenda" acessível (`aria-describedby`, abre com foco/clique, fecha com Esc); `glossario: Record<TermoGlossario, {titulo, texto}>`; `Estado` (`carregando` | `vazio` | `erro` com `onTentarDeNovo`); `AvisoRisco`.

- [ ] Teste: `proxy` sem cookie em `/terminal` → 307 para `/login?proximo=%2Fterminal`; com cookie → passa; `/login` sem cookie → passa.
- [ ] Teste: `Dica` mostra o texto do glossário ao clicar e some com Esc.
- [ ] Workflow `frontend.yml` (push e pull_request em `frontend/**` e no próprio arquivo): `npm install`, `npm run lint`, `npm run typecheck` (`next typegen && tsc --noEmit`), `npm test`, `npm run build`, `npx playwright install --with-deps chromium`, `npm run e2e`; relatório do Playwright como artefato em falha.
- [ ] Push e confirmar que os testes falham no CI antes de implementar; implementar; CI verde; commit.

### Task 2: Camada de API e WebSocket

**Files:** `src/lib/api/{tipos.ts,cliente.ts,endpoints.ts}`, `src/lib/ws/cliente.ts`. Tests: `tests/api/cliente.test.ts`, `tests/ws/cliente.test.ts`.

**Interfaces — Produces:**
- Tipos do contrato: `Usuario`, `Ativo`, `Candle`, `CandleAoVivo`, `TempoGrafico`, `Analise`, `Expiracao`, `Direcao`, `Sinal`, `SinalHistorico`, `Plano`, `PayoutExnova`, admin (`UsuarioAdmin`, `EventoAcesso`, `EventoAuditoria`, `EventoQualidade` — campos além do contrato marcados opcionais).
- `class ErroApi extends Error {status; codigo; mensagem}`; `requisicao<T>(caminho: string, opcoes?: {metodo?, corpo?, sinal?, semRedirecionar?}): Promise<T>`; `definirTratadorSessao(t: {aoNaoAutenticado(): void; aoAssinaturaVencida(): void})`.
- `api.*` em `endpoints.ts` (uma função por rota do contrato).
- `class ClienteTempoReal { constructor(opcoes: {url, criarSocket?, agendar?, aleatorio?, aoMudarStatus?, aoSessaoRevogada?, aoAssinaturaVencida?}); assinar<C extends Canal>(canal: C, ouvinte: (dados: DadosDoCanal<C>) => void): () => void; fechar(): void }`; `atrasoReconexao(tentativa, aleatorio): number`.

- [ ] Testes do cliente HTTP: CSRF em POST/PATCH/PUT e ausente em GET; 401 chama `aoNaoAutenticado` (não chama com `semRedirecionar`); 402 chama `aoAssinaturaVencida`; 429 dá a mensagem fixa; corpo não JSON (Review Focus 3) dá "Erro inesperado (502)"; 204 devolve `undefined`.
- [ ] Testes do WebSocket (socket falso): assina ao abrir; mensagem só chega ao ouvinte do canal; cancelar quando o último ouvinte sai; fecho 1006 → reconecta após `atrasoReconexao(0)` e reassina (Review Focus 2); 4401/4402 não reconectam e chamam o callback; atraso cresce e tem teto de 30 s.
- [ ] Implementar, CI verde, commit.

### Task 3: Sessão, login, assinatura e perfil

**Files:** `src/components/sessao/ProvedorSessao.tsx` (`useSessao(): {usuario, carregando, definirModo(m), atualizar()}`), `src/app/login/page.tsx` + `src/components/auth/FormLogin.tsx`, `src/app/assinatura/page.tsx`, `src/app/(app)/layout.tsx` (cabeçalho, navegação, alternador de modo, sair, aviso de risco), `src/app/(app)/perfil/page.tsx`, `src/components/perfil/FormSenha.tsx`. Tests: `tests/auth/form-login.test.tsx`, `tests/perfil/form-senha.test.tsx`, `tests/sessao/modo.test.tsx`.

- [ ] Testes: login inválido mostra a mensagem do servidor; `totp_necessario` mostra o passo do código (6 dígitos, `autocomplete="one-time-code"`) e reenvia com `totp`; sucesso navega para `proximo` ou `/terminal`; senha nova < 10 caracteres bloqueia o envio; confirmação diferente bloqueia; 204 mostra sucesso; alternar modo chama `PATCH /api/eu/preferencias {modo}`.
- [ ] Implementar, CI verde, commit.

### Task 4: Terminal e gráfico

**Files:** `src/lib/indicadores.ts` (`ema`, `sma`, `bollinger`, `vwap`, `rsi`, `macd` sobre `number[]`/candles, `NaN`-livres: devolvem `(number|null)[]`), `src/lib/desenhos.ts` (tipos `Desenho`, leitura/gravação no `layout`), `src/components/terminal/{Terminal.tsx,ListaAtivos.tsx,SeletorTempo.tsx,Grafico.tsx,BarraFerramentas.tsx,primitivaZona.ts}`, `src/lib/ws/usarCanal.ts`. Tests: `tests/indicadores.test.ts`, `tests/terminal/lista-ativos.test.tsx`, `tests/terminal/candles-ao-vivo.test.ts`.

- [ ] Testes de indicadores com valores calculados à mão (EMA 3 de 1..5 = [null,null,2,3,4]; RSI 14 só ganhos = 100; Bollinger de série constante tem banda = média; VWAP de candles iguais = preço típico; MACD de série constante = 0).
- [ ] Teste `mesclarCandle(lista, aoVivo)`: substitui o último de mesmo `t`, anexa o novo, ignora `t` antigo (Review Focus 4).
- [ ] Teste `ListaAtivos`: ativo fechado aparece como "Fechado" e desabilitado.
- [ ] Gráfico: velas + volume (escala sobreposta), EMA 9/21, Bollinger 20/2, VWAP sobre o preço; RSI e MACD em painéis próprios (`addSeries(..., paneIndex)`); tempos `1m…1w`; linha horizontal (`createPriceLine`) e zona de preço (primitiva) salvas em `layout.desenhos[simbolo]` via `PATCH /api/eu/preferencias`.
- [ ] Implementar, CI verde, commit.

### Task 5: Análise, sinais e cartão de sinal

**Files:** `src/lib/sinais.ts` (`ordenarSinais(lista): (Sinal|null)[]` nas 5 expirações; `estadoJanela(janela_ate, agora): {dentro: boolean, restanteMs}`; `estatisticas(historico): {n, win, loss, tie, semDado, taxa|null}`), `src/components/terminal/{PainelAnalise.tsx,TabelaSinais.tsx,CartaoSinal.tsx}`. Tests: `tests/sinais.test.ts`, `tests/terminal/painel-analise.test.tsx`, `tests/terminal/tabela-sinais.test.tsx`, `tests/terminal/cartao-sinal.test.tsx`.

- [ ] Testes: tabela com 5 linhas na ordem certa mesmo com lista parcial/desordenada (Review Focus 5); AGUARDAR mostra motivo e "—" na probabilidade; COMPRA com `probabilidade 0.57, n 412` mostra "57,0%" e "n = 412".
- [ ] Testes do painel: `resumo` aparece; resistência com `toques ≥ 3` diz "difícil de romper"; modo Essencial esconde a grade de indicadores.
- [ ] Testes do cartão: contagem regressiva; quando `janela_ate` passa com o relógio avançado (`vi.useFakeTimers`) mostra "Fora da janela, não entre" (Review Focus 1); nota de expiração curta sempre presente em 1m/5m.
- [ ] Implementar, CI verde, commit.

### Task 6: Histórico

**Files:** `src/app/(app)/historico/page.tsx`, `src/components/historico/TabelaHistorico.tsx`. Test: `tests/historico/tabela-historico.test.tsx`.

- [ ] Teste: filtros (ativo, período) montam a query; resumo com taxa excluindo SEM_DADO e empates contados à parte; "apertado" marcado; vazio mostra estado vazio.
- [ ] Implementar, CI verde, commit.

### Task 7: Admin

**Files:** `src/app/admin/layout.tsx` (só `papel === "admin"`), páginas `usuarios`, `planos`, `assinaturas`, `acessos`, `auditoria`, `payout`, `qualidade`; `src/components/admin/*`. Tests: `tests/admin/usuarios.test.tsx`, `tests/admin/payout.test.tsx`.

- [ ] Testes: busca chama `GET /api/admin/usuarios?busca=…`; bloquear envia `PATCH {status:"bloqueado"}` após confirmação; criar valida e-mail e senha temporária ≥ 10; editor de payout rejeita valor fora de 0–100% e envia `PUT` com a lista inteira.
- [ ] Implementar, CI verde, commit.

### Task 8: E2E, documentação e PR

**Files:** `frontend/e2e/{mocks.ts,login.spec.ts,terminal.spec.ts,admin.spec.ts}`, `frontend/README.md`, `docs/fases/fase-09-frontend.md`.

- [ ] E2E (API e WebSocket simulados com `page.route` e `page.routeWebSocket`, rotulados como simulação): login com TOTP; terminal mostra tabela com 5 AGUARDAR, painel de análise e candle ao vivo; 402 leva a `/assinatura`; admin lista usuários.
- [ ] Documentar execução local e resultados do CI; abrir PR para `main`; iterar até CI verde. Não fazer merge.
