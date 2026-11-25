# Contrato da API v1 (backend ↔ frontend)

Fonte da verdade compartilhada entre o backend (FastAPI) e o frontend (Next.js). Mudanças neste arquivo exigem atualizar os dois lados.

## Convenções

- Base: `/api`. JSON em UTF-8. Instantes em **milissegundos UTC** (`int`). Preços como **string decimal** (precisão preservada); valores de análise como `number`.
- Autenticação por **cookie de sessão** `sinais_sessao` (httpOnly, Secure, SameSite=Lax). Mutações exigem o cabeçalho `X-CSRF-Token` igual ao cookie `sinais_csrf` (não httpOnly).
- Erros: `{"erro": {"codigo": "texto_curto", "mensagem": "Texto para o usuário"}}` com status HTTP adequado. `401` sem sessão, `402` assinatura vencida ou inexistente, `403` sem permissão, `422` validação, `429` limite de requisições.
- Toda rota de dados (fora de `/api/auth/*` e `/api/publico/*`) exige sessão **e** assinatura ativa, checadas no servidor.

## Autenticação e conta

| Método e rota | Corpo | Resposta |
|---|---|---|
| `POST /api/auth/login` | `{email, senha, totp?}` | `200 {usuario: Usuario}` + cookies. `401` credenciais inválidas (mensagem genérica). `423` conta bloqueada. Admin sem `totp` → `401 {codigo: "totp_necessario"}` |
| `POST /api/auth/logout` | — | `204` |
| `GET /api/eu` | — | `200 Usuario` |
| `POST /api/eu/senha` | `{senha_atual, senha_nova}` (nova ≥ 10 caracteres) | `204`; derruba as outras sessões |
| `PATCH /api/eu/preferencias` | `{modo?: "essencial"\|"avancado", layout?: object}` | `200 Usuario` |

`Usuario = {id, email, nome, papel: "cliente"|"admin", modo: "essencial"|"avancado", assinatura: {plano, status: "ativa"|"vencida"|"bloqueada", vence_em: int|null}}`

## Mercado

| Método e rota | Resposta |
|---|---|
| `GET /api/ativos` | `[{simbolo: "BTCUSDT", nome: "Bitcoin", classe: "cripto", aberto: true}]` |
| `GET /api/candles?simbolo=BTCUSDT&tg=1m&ate=<ms>&limite=500` | `[{t, o, h, l, c, v}]` em ordem crescente, só candles fechados. `tg ∈ 1m,3m,5m,15m,30m,1h,4h,1d,1w`. `limite ≤ 1500` |
| `GET /api/analise?simbolo=BTCUSDT` | `Analise` (abaixo) do último minuto fechado |
| `GET /api/sinais?simbolo=BTCUSDT` | `[{expiracao: "1m"\|"5m"\|"15m"\|"30m"\|"60m", direcao: "COMPRA"\|"VENDA"\|"AGUARDAR", probabilidade: number\|null, n_validacao: int\|null, motivo: string, janela_ate: int\|null, invalidacao: string\|null, modelo: string\|null}]` |
| `GET /api/sinais/historico?simbolo=&inicio=&fim=` | `[{id, simbolo, expiracao, direcao, gerado_em, preco_referencia, resultado: "WIN"\|"LOSS"\|"TIE"\|"SEM_DADO"\|null, apertado: bool\|null}]` |

`Analise = {simbolo, t, preco, tendencia: {"1m"|"5m"|"15m"|"1h": -1|0|1}, forca_tendencia: number (ADX), regioes: {resistencia: {preco, distancia_atr, toques}|null, suporte: {...}|null}, estrutura: {ultimo_evento: "BOS_ALTA"|"BOS_BAIXA"|"CHOCH_ALTA"|"CHOCH_BAIXA"|null, topo: number|null, fundo: number|null}, volume: {relativo, pressao_compradora}, indicadores: {rsi, macd_hist, estoc_k, bb_pct, atr}, price_action: {impulso, desaceleracao, lateral: bool}, resumo: string[]}`

`resumo` traz frases curtas montadas por template só a partir desses números (ex.: "Tendência de alta em 15m e 1h", "Preço a 0,4 ATR de uma resistência tocada 5 vezes"). Nenhum número é inventado.

**Enquanto nenhum modelo estiver aprovado**, `/api/sinais` devolve `AGUARDAR` em todas as expirações, com `motivo: "Nenhum modelo validado para esta expiração"` e `probabilidade: null`.

## Tempo real

`GET /api/ws` (WebSocket, mesma sessão por cookie). O cliente envia `{"acao": "assinar", "canal": "candles:BTCUSDT:1m"}` ou `"analise:BTCUSDT"` ou `"sinais:BTCUSDT"`, e `{"acao": "cancelar", "canal": ...}`. O servidor envia `{"canal": ..., "dados": ...}`:
- `candles`: `{t, o, h, l, c, v, fechado: bool}`. O candle em formação vai com `fechado=false`, só para o gráfico.
- `analise`: `Analise`.
- `sinais`: a lista de `/api/sinais`.

O servidor fecha com código `4401` quando a sessão é revogada e `4402` quando a assinatura vence.

## Administração (papel `admin`, 2FA obrigatório)

| Método e rota | Uso |
|---|---|
| `GET /api/admin/usuarios?busca=&status=` · `POST /api/admin/usuarios` · `PATCH /api/admin/usuarios/{id}` | Listar, criar (`{email, nome, senha_temporaria, plano, vence_em}`), editar, bloquear (`{status: "bloqueado"}`), desativar |
| `GET/POST/PATCH /api/admin/planos` | `{id, nome, duracao_dias, preco_centavos, recursos: {ativos: [], expiracoes: [], modo_avancado: bool, cursos: bool}, ativo}` |
| `POST /api/admin/assinaturas` | `{usuario_id, plano_id, inicio, fim}` (criar ou renovar) |
| `GET /api/admin/acessos?usuario_id=` | Log de acesso |
| `GET /api/admin/auditoria` | Ações dos admins |
| `GET/PUT /api/admin/corretoras/exnova/payout` | `[{simbolo, expiracao, payout}]` |
| `GET /api/admin/qualidade` | Eventos de qualidade de dados recentes |

## Público

| Método e rota | Uso |
|---|---|
| `GET /api/publico/estatisticas` | Estatísticas agregadas por ativo e expiração (n, taxa, período), sem sinais individuais recentes |
