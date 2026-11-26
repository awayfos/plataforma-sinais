# Fase 9 — Plataforma web (frontend) e interface do admin

- **Status:** implementada no PR #13 (`plataforma-frontend`) e integrada ao backend em `main`; correções da revisão de integração no branch `integracao-correcoes` (seção 2.4). Aguarda revisão e aprovação visual do cliente.
- **Plano:** `docs/superpowers/plans/2026-11-25-plataforma-frontend.md`
- **Contrato:** `docs/api/contrato-v1.md` (o frontend foi escrito contra ele; o backend da Fase 8 é desenvolvido em paralelo)
- **Como rodar:** `docs/COMO-RODAR-LOCAL.md` (passo a passo completo) e `frontend/README.md`

## 1. O que foi construído

| Área | Telas e componentes | Rotas do contrato |
|---|---|---|
| Autenticação | `/login` (passo TOTP para admin), sair, `/assinatura` (assinatura vencida ou bloqueada), `src/proxy.ts` só confere se o cookie existe | `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/eu` |
| Terminal | `/terminal`: lista de ativos (aberto/fechado), gráfico de velas e volume, tempos 1m–1w, zoom, EMA 9/21, Bollinger 20/2, VWAP, painéis RSI 14 e MACD 12/26/9, linha horizontal e zona de preço, alerta sonoro opcional | `GET /api/ativos`, `GET /api/candles`, WebSocket `candles:*` |
| Análise | Painel com preço, `resumo`, tendência por tempo gráfico (texto e ícone, não só cor), resistência e suporte com distância em ATR, toques e selo "difícil de romper" (≥ 3 toques), estrutura (BOS/CHoCH), volume relativo, pressão compradora, impulso, desaceleração, lateral; no Avançado, ADX, topo/fundo e indicadores | `GET /api/analise`, WebSocket `analise:*` |
| Sinais | Tabela com uma linha por expiração (1, 5, 15, 30 min e 1 h): COMPRA/VENDA/AGUARDAR, probabilidade calibrada com n só quando enviada, motivo do AGUARDAR, nota explicando por que tudo está em AGUARDAR. Cartão do sinal ativo: contagem regressiva da janela, "Fora da janela, não entre", invalidação, estatísticas dos últimos 30 dias da mesma expiração, aviso de entrada precisa em 1 e 5 min | `GET /api/sinais`, WebSocket `sinais:*`, `GET /api/sinais/historico` |
| Modos | Essencial e Avançado salvos nas preferências; ícone "aprenda" (glossário com 27 termos) em cada termo técnico | `PATCH /api/eu/preferencias {modo}` |
| Layout | Ativo, tempo gráfico, indicadores e desenhos salvos | `PATCH /api/eu/preferencias {layout}` |
| Histórico | `/historico`: filtros por ativo, expiração e período, resumo (taxa = WIN/(WIN+LOSS), empates e "sem dado" à parte, apertados), tabela com todas as derrotas | `GET /api/sinais/historico` |
| Perfil | `/perfil`: conta, plano, situação e vencimento, modo, resumo do histórico, troca de senha (≥ 10 caracteres) | `GET /api/eu`, `POST /api/eu/senha` |
| Admin | `/admin/usuarios` (busca, filtro de status, criar, editar, bloquear com confirmação, desbloquear, renovar), `/admin/planos`, `/admin/assinaturas`, `/admin/acessos`, `/admin/auditoria`, `/admin/payout` (com equilíbrio p* = 1/(1+r)), `/admin/qualidade` | rotas `/api/admin/*` |
| Aviso de risco | Faixa permanente e discreta no rodapé de todas as telas logadas e na de assinatura | — |

Camada técnica:
- `src/lib/api`: tipos espelhando o contrato, cliente HTTP com `X-CSRF-Token` (cookie `sinais_csrf`) nas mutações, `credentials: same-origin`, erros `{erro: {codigo, mensagem}}`, 401 → login, 402 → assinatura, 429 → mensagem fixa, corpo não JSON → mensagem genérica com o status.
- `src/lib/ws`: um WebSocket por aba, multiplexado por canal, tipado (`DadosDoCanal<C>`), reassina tudo ao reconectar, backoff exponencial com jitter (0,5 s a 30 s), 4401 → login e 4402 → assinatura, sem reconexão.
- Preços exibidos a partir da string decimal, sem `float`; horários em Brasília.

## 2. Decisões tomadas (rulings)

1. `src/proxy.ts` em vez de `middleware.ts`: no Next.js 16 o arquivo e a função foram renomeados.
2. `layout`: o frontend grava com `PATCH` e lê `usuario.layout` (o backend devolve desde o PR #14); a cópia no `localStorage` só vale quando o servidor não tem nada salvo.
3. Tolerância de preço e preço de referência (design §12.6): o cartão mostra `tolerancia_preco` e `preco_referencia` quando vêm (no contrato desde o PR #14; nulos em AGUARDAR).
4. As estatísticas do cartão são calculadas no navegador a partir de `/api/sinais/historico` (dados reais, mesma regra do histórico).
5. "Difícil de romper" a partir de 3 toques (o contrato não fixa o limite). O número de toques aparece sempre.
6. Indicadores do gráfico calculados no navegador, só para exibição; a análise oficial vem do backend.
7. Eixo do gráfico em UTC−3 fixo (o Brasil não tem horário de verão desde 2019).
8. Desenhos salvos por ativo (valem em todos os tempos gráficos).
9. `.npmrc` com `legacy-peer-deps=true`: o npm 10.9 do CI quebra ao resolver os peers opcionais vitest → jsdom → `@napi-rs/canvas` (`Cannot read properties of null (reading 'edgesOut')`). Conferido de novo em 2026-11-26: sem a opção, a geração do lock ainda falha. Todos os peers necessários estão declarados.
10. `package-lock.json` gerado no CI (o ambiente de desenvolvimento não tem acesso ao registro npm) e versionado; os três jobs usam `npm ci`. Versões travadas: Next 16.4.6, React 19.3.1, TypeScript 5.9.3, Vitest 4.1.12, Playwright 1.65.1, Lightweight Charts 5.3.0.

## 2.1 Correções da revisão independente (PR #13)

Cada correção teve um teste enviado antes e visto falhando no CI (commit `7c8a582`: 14 testes falhando), depois verde com a correção (`d3cdce1`).

| Item | Correção | Teste (vermelho → verde) |
|---|---|---|
| I1 | `destinoSeguro` recusa caracteres de controle e `\`, confere a origem com `new URL` e devolve caminho + consulta + âncora | `form-login.test.tsx` › rejeita caracteres de controle e barra invertida; mantém caminho interno codificado |
| I2 | Contagem da janela pelo relógio do servidor (cabeçalho `Date`, meio do segundo) menos 1 s de margem | `cartao-sinal.test.tsx` › usa o relógio do servidor…; com o cliente adiantado…; `cliente.test.ts` › registra o relógio do servidor pelo cabeçalho Date |
| I3 | Ao reconectar, recarrega candles, análise e sinais (mantendo os dados na tela); sem tempo real, aviso "desatualizados" e painéis esmaecidos; status da conexão também no celular | `terminal.test.tsx` › marca os dados como desatualizados na queda e recarrega tudo ao reconectar |
| I4 | A cada 3 quedas seguidas sem conexão estável, `GET /api/eu` (401/402 redirecionam) | `ws/cliente.test.ts` › após 3 falhas seguidas…; uma conexão aberta zera a contagem |
| I5 | Lista de sinais do WebSocket vale só para o ativo e a conexão em que chegou; limpa ao trocar de ativo | `terminal.test.tsx` › sinais antigos do WebSocket não vencem o REST novo |
| I6 | Barras 1d/1w sem deslocamento de fuso; VWAP desabilitado em 1d/1w, âncora documentada (00:00 UTC) | `candles-ao-vivo.test.ts` › tempoDoGrafico; `barra-ferramentas.test.tsx` › VWAP só em tempos intradiários |
| I7 | Probabilidade só com direção diferente de AGUARDAR, valor e n | `tabela-sinais.test.tsx` › probabilidade sem n…; AGUARDAR nunca mostra probabilidade; `cartao-sinal.test.tsx` › probabilidade sem n… |
| I8 | Lockfile versionado, `npm ci`, cache do npm, `permissions: contents: read` | CI verde com `npm ci` |
| I9 | Histórico sem AGUARDAR (lista e contas) e paginação de 50 | `tabela-historico.test.tsx` › não lista AGUARDAR e pagina de 50 em 50; `sinais.test.ts` › AGUARDAR não entra nas estatísticas |
| M2 | Senha atual errada (422/403) mostra a mensagem sem encerrar a sessão (já funcionava; teste passou de primeira) | `form-senha.test.tsx` › senha atual errada (422/403)… |
| M4 | Tempo gráfico ausente na análise mostra "—", não "Lateral" | `painel-analise.test.tsx` › tempo gráfico ausente… |
| M6 | Nota "AGUARDAR em todas" só quando as 5 linhas são AGUARDAR | `tabela-sinais.test.tsx` › nota de AGUARDAR em todas… |
| M10 | Legenda do gráfico não mistura séries ao trocar de ativo | `candles-ao-vivo.test.ts` › legendaVisivel |

Itens menores da revisão deixados para depois: M1, M3, M5, M7, M8, M9, M11, M12.

## 2.2 Alinhamento com o backend (PR #14)

Testes enviados antes (`7a2a390`: 8 falhando), verdes com a correção (`273c2e9`).

| Item | O que mudou | Teste |
|---|---|---|
| 1 | `assinatura.plano` pode ser `null`: perfil e tela de assinatura mostram "Sem plano" | `perfil.test.tsx` › usuário sem assinatura… |
| 2 | Campos numéricos da `Analise` podem ser `null` (ADX, volume, indicadores, impulso, desaceleração): mostram "—" | `painel-analise.test.tsx` › valores nulos… |
| 3 | `Analise.t` é a abertura do último candle de 1m fechado: o painel mostra o minuto como intervalo (ex.: 10:30–10:31) | `painel-analise.test.tsx` › t é a abertura… |
| 4 | `tolerancia_preco` numérica (unidades de preço), `preco_referencia` string | `cartao-sinal.test.tsx` › tolerância de preço… (passou de primeira: só tipo) |
| 5 | Canal de candles só com `fechado: true` funciona (cada fechamento anexa a barra) | `serie-ao-vivo.test.ts` |
| 6 | Quadros de erro `{canal, erro}` não chegam como dados; o terminal mostra a mensagem (ex.: ativo fora do plano) | `ws/cliente.test.ts` › quadro de erro…; `terminal.test.tsx` › erro do canal… |
| 7 | Handshake recusado (4403 → 1006) com `/api/eu` válido: para o laço rápido, status "Ao vivo indisponível" e nova tentativa a cada minuto | `ws/cliente.test.ts` › modo lento…; `terminal.test.tsx` › handshake recusado… |
| 8 | Admin: redefinir senha temporária (`PATCH {senha_temporaria}`); id numérico do plano ao criar usuário | `usuarios.test.tsx` › redefinir senha…; criar envia o id numérico… |
| 9 | Layout do servidor lido primeiro (`usuario.layout`); cópia local só se o servidor não tiver nada | — (já lia primeiro; só o comentário e o caso `{}` mudaram) |
| 10 | Encerrar assinatura antes do fim: feito na revisão de integração (botão "Encerrar" em `/admin/usuarios`, seção 2.4) | `usuarios.test.tsx` › encerrar assinatura |

## 2.3 Gráfico tick a tick (como na Binance)

Testes enviados antes (`06af23b`: 4 arquivos e 3 testes falhando; o e2e não chegou a rodar porque o build também faz checagem de tipos dos testes), verdes com a implementação (`5bd1a77`, `b30d251`).

- `lib/serieAoVivo.ts`: mesmo `t` substitui a última barra; `t` maior anexa; `t` menor é ignorado (exceto o `fechado: true` oficial, que substitui a barra de mesmo `t` entre as últimas 5, ver 2.4); depois de `fechado: true` (ou de uma barra vinda do REST) um tick em formação do mesmo `t` é ignorado; tick de outro canal (troca de ativo ou de tempo gráfico) é descartado; o snapshot que chega antes do REST é guardado e reaplicado; recarregar o REST no mesmo canal (reconexão) mantém a barra em formação mais nova. Testes: `serie-ao-vivo.test.ts`.
- `lib/agrupador.ts`: os ticks de um quadro são aplicados juntos no `requestAnimationFrame`, com fila limitada (aba em segundo plano). Teste: `agrupador.test.ts`.
- `lib/indicadoresIncrementais.ts`: EMA 9/21, Bollinger, VWAP, RSI e MACD recalculam só a barra tocada; o resultado bate com o cálculo completo depois de ticks e barras novas. Teste: `indicadores-incrementais.test.ts`.
- `Grafico.tsx`: os ticks não passam pelo estado do React. Cada quadro chama `update` só nas barras tocadas (velas, volume e indicadores), sem `setData`. A legenda OHLC é escrita direto no DOM. A linha e o rótulo do último preço ficam na cor da barra (alta/baixa), com a contagem até o fechamento no eixo (ex.: "00:37"), pelo relógio do servidor. Teste: `formato.test.ts` › contagem até o fechamento.
- Preço ao vivo com piscada verde/vermelha no cabeçalho e na lista de ativos (`PrecoAoVivo`, `useSyncExternalStore`: só o número re-renderiza). Usa os ticks do gráfico e o canal opcional `preco:SIMB`. Teste: `precos.test.tsx`.
- E2E `ticks.spec.ts`: o WebSocket simulado envia o snapshot e mais 50 ticks em 5 s no mesmo `t`. O fechamento da última barra termina igual ao último tick e a quantidade de barras não muda durante os ticks.

## 2.4 Correções da revisão de integração (`integracao-correcoes`)

Testes enviados antes (`bec0014`: 10 testes falhando no CI), verdes com a correção (`f38b8a9`).

| Item | O que mudou | Teste |
|---|---|---|
| I1 | O 1m oficial (`fechado: true`) chega 1–2 s depois dos primeiros ticks da barra seguinte e era descartado. Agora substitui a barra de mesmo `t` entre as últimas 5; o gráfico atualiza as barras tocadas em ordem de tempo (`update(barra, historicalUpdate)`) e os indicadores são recalculados daquela barra até o fim | `serie-ao-vivo.test.ts` › fechamento oficial depois de 3 ticks…, mesmo quadro…; `indicadores-incrementais.test.ts` › oficial atrasado… |
| I4 | Histórico "Todos" e o resumo do Perfil chamam sem `simbolo` (o backend agora aceita) | `tabela-historico.test.tsx`, `perfil.test.tsx` |
| I5 | Documentação: WebSocket direto só por `ws://localhost:8000/api/ws`, nunca `127.0.0.1` (o cookie é do host `localhost`) | — |
| M10 | Contagem do rótulo de preço avança pelo relógio para o próximo período quando não chega tick (não para em 00:00); deslocamento do relógio do servidor = mediana das últimas 7 amostras | `contagem-vela.test.ts`, `relogio.test.ts` |
| M11 | Ticks guardados de canais ainda não carregados: no máximo 3 canais, descartados ao cancelar a assinatura e ao carregar outro canal | `serie-ao-vivo.test.ts` › espera limitada… |
| Admin | Botão "Encerrar" (com confirmação) para a assinatura vigente | `usuarios.test.tsx` › encerrar assinatura… |
| E2E real | `e2e-real/terminal-real.spec.ts` + `playwright.real.config.ts`: contra o backend real do Compose (job `e2e-real` do CI) | o próprio teste |

## 3. Pontos do contrato para o backend

Itens 1 a 6 resolvidos no PR #14 (ver `docs/fases/fase-07-08-10-backend.md`, "Acréscimos pedidos pelo frontend"); 7 e 8 continuam abertos.

1. Devolver `layout` em `GET /api/eu` (hoje só existe a escrita).
2. Incluir no `Sinal` a tolerância de preço e o preço de referência da janela de entrada (design §12.6).
3. Fixar o formato das respostas de `GET /api/admin/usuarios` (status do usuário, assinatura), `acessos`, `auditoria`, `qualidade` e `/api/publico/estatisticas`. O frontend usa campos opcionais: `UsuarioAdmin {id, email, nome, papel?, status?, assinatura?}`, `EventoAcesso {ts, evento, usuario_id?, email?, ip?, user_agent?}`, `EventoAuditoria {ts, acao, admin_id?, admin_email?, alvo?, antes?, depois?}`, `EventoQualidade {tipo, simbolo?, inicio?, fim?, detalhes?}`.
4. Deixar `GET /api/eu` e `POST /api/eu/senha` fora da exigência de assinatura ativa, para a tela de assinatura mostrar o plano e o usuário poder trocar a senha.
5. `PATCH /api/admin/planos` não tem id na rota: o frontend envia o plano inteiro, com `id`, no corpo.
6. Payout em fração (0,86); o editor mostra e aceita porcentagem.
7. Para a janela de entrada, o ideal é o servidor mandar a própria hora (ex.: campo `servidor_ms` nas mensagens de `sinais`); hoje o frontend estima pelo cabeçalho `Date`, com resolução de 1 s.
8. `/api/sinais/historico` não tem limite nem paginação no contrato; o frontend pagina na tela.

## 4. Testes e CI

Workflow `.github/workflows/frontend.yml` (push e pull request em `frontend/**`, `permissions: contents: read`, instalação com `npm ci`), três jobs em paralelo:

| Job | Passos |
|---|---|
| Lint e tipos | `npm ci`, `npm run lint` (ESLint 9 + `eslint-config-next` 16), `npm run typecheck` (`next typegen && tsc --noEmit`) |
| Testes (Vitest) | `npm test` |
| Build e E2E | `npm run build`, `npx playwright install --with-deps chromium`, `npm run e2e` contra `next start`, capturas de tela |

Processo: os testes foram enviados antes da implementação e falharam no CI (18 de 18 arquivos, "Failed to resolve import"); depois a implementação os deixou verdes.

Resultado no CI (versões resolvidas: Next 16, React 19.3.1, TypeScript 5.9.3, Tailwind 4.3.5, Lightweight Charts 5.3.0, Vitest 4.1.12, Playwright 1.65.1):

- Vitest (depois das correções da revisão, do alinhamento com o backend e do gráfico tick a tick): **27 arquivos, 127 testes, todos passando**. Primeira versão: 18 arquivos, 77 testes (API e CSRF, WebSocket e reconexão, proxy, indicadores com valores calculados à mão, formatação pt-BR, login com TOTP, troca de senha, modo, lista de ativos, candle ao vivo, tabela de sinais, painel de análise, cartão com janela, histórico, usuários e payout do admin).
- Lint: 0 erros (4 avisos de `window.location.assign`, mantido de propósito para recarregar a página e limpar o estado ao perder a sessão).
- Build: 16 rotas.
- Playwright: **11 testes passando** (inclui `ticks.spec.ts`) — login com TOTP, credenciais inválidas, terminal com 5 AGUARDAR e candle ao vivo pelo WebSocket simulado, modo Avançado salvo, 402 → assinatura, troca de tempo gráfico, admin lista usuários, cliente sem acesso ao admin, e capturas de tela (terminal Avançado e Essencial, celular, histórico, perfil, admin, login). Os dados das simulações ficam em `frontend/e2e/mocks.ts`, rotulados como simulação.

Revisão visual: as capturas do CI saem também no log do job (em base64), porque o ambiente de desenvolvimento não acessa o armazenamento de artefatos do GitHub. A revisão delas encontrou e corrigiu: o gráfico passava da altura da janela e escondia o volume e o painel RSI; campos de busca do admin com classes de largura em conflito; seletor de modo esticado no perfil; cabeçalho apertado no celular.

## 5. Pendências

- Revisão visual pelo cliente (critério da Fase 9).
- Latência de ponta a ponta medida com o backend real (critério da Fase 9). O job `e2e-real` já prova o caminho navegador → Next → API → Redis → Binance com ticks reais; a medição de latência ainda não foi feita.
- Página pública de estatísticas (`/api/publico/estatisticas`): o formato está fixado no contrato; a página ainda não existe.
- CSP com nonce e cabeçalhos HSTS ficam para a Fase 11 (hoje: `X-Frame-Options`, `nosniff`, `Referrer-Policy`, `Permissions-Policy`).
