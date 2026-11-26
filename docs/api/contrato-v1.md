# Contrato da API v1 (backend ↔ frontend)

Fonte da verdade compartilhada entre o backend (FastAPI) e o frontend (Next.js). Mudanças neste arquivo exigem atualizar os dois lados. O esquema gerado do código fica em `docs/api/openapi-v1.json` (o CI confere que é igual ao código).

## Convenções

- Base: `/api`. JSON em UTF-8. Instantes em **milissegundos UTC** (`int`). Preços como **string decimal** (precisão preservada); valores de análise como `number` (`null` quando ainda não há histórico para calculá-los).
- Autenticação por **cookie de sessão** `sinais_sessao` (httpOnly, Secure, SameSite=Lax, Path=/). Mutações exigem o cabeçalho `X-CSRF-Token` igual ao cookie `sinais_csrf` (não httpOnly, para o JavaScript ler).
- Cookie **`sinais_dispositivo`** ("dispositivo confiável"; httpOnly, Secure, SameSite=Strict, Path=/api/auth, 90 dias): emitido em todo login bem-sucedido, assinado (HMAC) e amarrado ao e-mail. Quem o apresenta não é barrado pelo teto global de falhas do e-mail (ataque distribuído), só pelo bloqueio progressivo do próprio (e-mail, IP). Sobrevive ao logout.
- `Secure` vem de `SINAIS_COOKIE_SEGURO` (padrão `true`; `false` só no desenvolvimento, e a configuração de produção recusa).
- Erros: `{"erro": {"codigo": "texto_curto", "mensagem": "Texto para o usuário"}}`. A tela mostra `mensagem`; o código serve para decidir o comportamento.
- Toda rota de dados (fora de `/api/auth/*`, `/api/eu*` e `/api/publico/*`) exige sessão **e** assinatura ativa, checadas no servidor em cada requisição. Admin não precisa de assinatura.

### Códigos de status

| Status | Quando | `codigo` |
|---|---|---|
| `401` | sem sessão, sessão revogada/expirada/ociosa; login inválido | `sessao_invalida`, `credenciais_invalidas` (mensagem genérica, igual para e-mail inexistente), `totp_necessario`, `totp_invalido` |
| `402` | assinatura vencida ou inexistente (só rotas de dados) | `assinatura_vencida` |
| `403` | sem permissão; CSRF ausente/errado; ativo ou recurso fora do plano | `sem_permissao`, `csrf_invalido`, `ativo_nao_incluido`, `recurso_nao_incluido` |
| `404` | recurso inexistente | `nao_encontrado`, `ativo_desconhecido`, `analise_indisponivel`, `usuario_inexistente`, `plano_inexistente`, `assinatura_inexistente` |
| `409` | conflito de unicidade | `email_em_uso`, `plano_existente` |
| `422` | validação (inclusive corpo ilegível ou aninhado demais) | `validacao`, `periodo_invalido`, `senha_fraca`, `senha_atual_incorreta`, `email_invalido`, `vencimento_invalido`, `plano_invalido`, `plano_inexistente`, `acao_invalida`, `layout_invalido`, `layout_grande` |
| `423` | login bloqueado (bloqueio progressivo, teto global ou conta bloqueada pelo admin) | `conta_bloqueada` |
| `429` | limite de tentativas (login por IP e por e-mail+IP, troca de senha por sessão) | `muitas_tentativas` |
| `500` | erro interno (nunca com detalhes) | `erro_interno` |

## Autenticação e conta

| Método e rota | Corpo | Resposta |
|---|---|---|
| `POST /api/auth/login` | `{email, senha, totp?}` | `200 {usuario: Usuario}` + cookies `sinais_sessao`, `sinais_csrf` e `sinais_dispositivo`. Admin sem `totp` → `401 totp_necessario`. Bloqueio progressivo por (e-mail, IP) a partir da 5ª falha (60 s, dobrando até 30 min); teto global por e-mail; IPv6 conta por bloco /64 |
| `POST /api/auth/logout` | — | `204` sempre (com ou sem sessão válida, com ou sem assinatura); com sessão válida exige CSRF e revoga a sessão |
| `GET /api/eu` | — | `200 Usuario`. Só exige sessão: funciona com assinatura vencida (a tela de assinatura usa) |
| `POST /api/eu/senha` | `{senha_atual, senha_nova}` (nova com 10 a 256 caracteres) | `204`; derruba as outras sessões. Até 5 tentativas por sessão a cada 15 min |
| `PATCH /api/eu/preferencias` | `{modo?: "essencial"\|"avancado", layout?: object}` | `200 Usuario`. `layout` é livre (definido pelo frontend), até 64 KiB e 16 níveis. Modo avançado fora do plano → `403 recurso_nao_incluido` |

`Usuario = {id, email, nome, papel: "cliente"|"admin", modo: "essencial"|"avancado", layout: object, assinatura: {plano: string|null, status: "ativa"|"vencida"|"bloqueada", vence_em: int|null}}` (`layout` é `{}` quando nada foi salvo).

## Mercado

| Método e rota | Resposta |
|---|---|
| `GET /api/ativos` | `[{simbolo: "BTCUSDT", nome: "Bitcoin", classe: "cripto", aberto: true}]` — só os ativos do plano |
| `GET /api/candles?simbolo=BTCUSDT&tg=1m&ate=<ms>&limite=500` | `[{t, o, h, l, c, v}]` em ordem crescente, só candles fechados (oficiais). `tg ∈ 1m,3m,5m,15m,30m,1h,4h,1d,1w`. `limite ≤ 1500`. Semana começa segunda 00:00 UTC |
| `GET /api/analise?simbolo=BTCUSDT` | `Analise` (abaixo) do último minuto fechado. `404 analise_indisponivel` enquanto o motor não publicou a primeira |
| `GET /api/sinais?simbolo=BTCUSDT` | `[Sinal]` das expirações do plano |
| `GET /api/sinais/historico?simbolo=&inicio=&fim=` | `[SinalHistorico]`. **`simbolo` é opcional**: sem ele, todos os ativos do plano do usuário (filtro "Todos" e resumo do Perfil); com ele, ativo fora do plano → `403`. `fim < inicio` → `422 periodo_invalido`. Vazio até o motor de sinais ao vivo gravar o primeiro |

Ativo desconhecido → `404 ativo_desconhecido`; fora do plano → `403 ativo_nao_incluido`.

`Sinal = {expiracao: "1m"|"5m"|"15m"|"30m"|"60m", direcao: "COMPRA"|"VENDA"|"AGUARDAR", probabilidade: number|null, n_validacao: int|null, motivo: string, janela_ate: int|null, invalidacao: string|null, modelo: string|null, tolerancia_preco: number|null, preco_referencia: string|null}`. `tolerancia_preco` (k × ATR, em preço) e `preco_referencia` (string decimal) descrevem a janela de entrada (design §12.6); são `null` enquanto a direção for `AGUARDAR`.

`SinalHistorico = {id, simbolo, expiracao, direcao, gerado_em, preco_referencia, resultado: "WIN"|"LOSS"|"TIE"|"SEM_DADO"|null, apertado: bool|null}`.

`Analise = {simbolo, t, preco, tendencia: {"1m"|"5m"|"15m"|"1h": -1|0|1}, forca_tendencia: number|null (ADX), regioes: {resistencia: {preco, distancia_atr, toques}|null, suporte: {...}|null}, estrutura: {ultimo_evento: "BOS_ALTA"|"BOS_BAIXA"|"CHOCH_ALTA"|"CHOCH_BAIXA"|null, topo: number|null, fundo: number|null}, volume: {relativo, pressao_compradora}, indicadores: {rsi, macd_hist, estoc_k, bb_pct, atr}, price_action: {impulso, desaceleracao, lateral: bool}, resumo: string[]}`

`resumo` traz frases curtas montadas por template só a partir desses números (ex.: "Tendência de alta em 15m e 1h", "Preço a 0,4 ATR de uma resistência tocada 5 vezes"). Nenhum número é inventado; tempo gráfico sem histórico aparece como "Sem dados de tendência em …".

**Enquanto nenhum modelo estiver aprovado**, `/api/sinais` devolve `AGUARDAR` em todas as expirações, com `motivo: "Nenhum modelo validado para esta expiração"` e `probabilidade: null`.

## Tempo real

`GET /api/ws` (WebSocket, mesma sessão por cookie). No desenvolvimento, conecte pelo mesmo host do frontend (`ws://localhost:3000/api/ws`, repassado pelo Next) ou direto em `ws://localhost:8000/api/ws` — sempre `localhost`, nunca `127.0.0.1`: o cookie é do host `localhost` e, sem ele, o servidor fecha com `4401` em laço.

O cliente envia `{"acao": "assinar", "canal": ...}` e `{"acao": "cancelar", "canal": ...}` (texto até 512 bytes). Canais:

| Canal | `dados` | Ao assinar (snapshot) |
|---|---|---|
| `candles:SIMB:TG` | `{t, o, h, l, c, v, fechado: bool}` | a vela em formação, se houver |
| `preco:SIMB` | `{preco, t}` (último negócio) | o último preço, se houver |
| `analise:SIMB` | `Analise` | a última análise, se houver |
| `sinais:SIMB` | a lista de `/api/sinais` (filtrada pelas expirações do plano) | a lista atual |

O servidor envia `{"canal": ..., "dados": ...}`.

- **`fechado: false`**: vela em formação montada negócio a negócio (aggTrade da Binance, igual à Binance: abertura = primeiro negócio, fechamento = último, máxima/mínima, volume = soma). Sai no máximo **uma vez a cada 100 ms** por canal (coalescida: vale o valor mais recente), só nos canais com assinantes. Serve só para o gráfico.
- **`fechado: true`**: o candle de 1m **oficial** da Binance (o mesmo que fica no banco), só em `candles:SIMB:1m`. Chega 1–2 s depois da virada do minuto, quando já pode ter havido `fechado: false` da barra seguinte: o cliente deve substituir a barra de mesmo `t` (não só a última). Os outros tempos gráficos são reconciliados no servidor (a vela em formação de 5m, 1h, 1w… soma os 1m oficiais do período + os negócios dos minutos abertos).
- Ao (re)assinar, o servidor manda o snapshot; depois de uma reconexão o cliente recarrega o REST.

Erros sem fechar a conexão:

- `{"erro": {"codigo": "mensagem_invalida", "mensagem": ...}}` — mensagem fora do formato, canal ou ativo desconhecido.
- `{"canal": ..., "erro": {"codigo": "ativo_nao_incluido", ...}}` — ativo fora do plano (também quando o plano muda com a conexão aberta: o canal é cancelado).
- `{"canal": ..., "erro": {"codigo": "limite_canais", ...}}` — no máximo **20 canais** por conexão.

Códigos de fechamento: `4401` sessão revogada ou expirada (não reconectar), `4402` assinatura vencida (não reconectar), `4403` origem (`Origin`) não permitida (`SINAIS_ORIGENS_PERMITIDAS`). Sessão e assinatura são conferidas na conexão, em cada `assinar` e a cada 5 s.

## Administração (papel `admin`, 2FA obrigatório)

| Método e rota | Corpo / uso | Resposta |
|---|---|---|
| `GET /api/admin/usuarios?busca=&status=` | busca por nome ou e-mail; `status ∈ ativo, bloqueado, desativado` | `[UsuarioAdmin]` |
| `POST /api/admin/usuarios` | `{email, nome, senha_temporaria (≥ 10), plano: id, vence_em?: ms}` (sem `vence_em`: duração do plano) | `201 UsuarioAdmin`; `409 email_em_uso`; `422 plano_inexistente` |
| `PATCH /api/admin/usuarios/{id}` | `{nome?, email?, status?: "ativo"\|"bloqueado"\|"desativado", senha_temporaria?}` | `200 UsuarioAdmin`; bloquear/desativar derruba as sessões; o admin não bloqueia a si mesmo (`422 acao_invalida`) |
| `GET /api/admin/planos` | — | `[Plano]` |
| `POST /api/admin/planos` | `Plano` sem `id` | `201 Plano`; `409 plano_existente` |
| `PATCH /api/admin/planos` · `PATCH /api/admin/planos/{id}` | campos a mudar (no primeiro, com `id` no corpo) | `200 Plano` |
| `POST /api/admin/assinaturas` | `{usuario_id, plano_id, inicio, fim}` (criar ou renovar) | `201 Assinatura` |
| `POST /api/admin/assinaturas/{id}/encerrar` | — (antecipa o fim para agora; auditado) | `200 Assinatura`; o cliente perde o acesso na hora (REST e WebSocket); `404 assinatura_inexistente` |
| `GET /api/admin/acessos?usuario_id=` | log de acesso (até 500) | `[{id, usuario_id, email, evento, ip, user_agent, t, ts}]` |
| `GET /api/admin/auditoria` | ações dos admins (até 500) | `[{id, admin_id, admin_email, acao, alvo, antes, depois, t, ts}]` |
| `GET /api/admin/corretoras/exnova/payout` · `PUT` (lista inteira) | `[{simbolo, expiracao, payout}]` | `payout` é **fração** (`0 < payout ≤ 1`, ex.: `0.86` = 86%) |
| `GET /api/admin/qualidade` | eventos de qualidade de dados recentes | `[{simbolo, intervalo, inicio, fim, tipo, detalhes}]` |

`UsuarioAdmin = Usuario + {status: "ativo"|"bloqueado"|"desativado", criado_em, assinatura_id: int|null}` (`assinatura_id` = assinatura vigente, usada pelo botão "Encerrar").

`Plano = {id, nome, duracao_dias, preco_centavos, recursos: {ativos: [], expiracoes: [], modo_avancado: bool, cursos: bool}, ativo}` · `Assinatura = {id, usuario_id, plano_id, inicio, fim, origem}`.

Toda mutação de admin exige CSRF e fica na auditoria (antes/depois).

## Público

| Método e rota | Uso |
|---|---|
| `GET /api/publico/estatisticas` | `[{simbolo, expiracao, n, taxa, inicio, fim}]` agregadas por ativo e expiração, sem sinais individuais recentes (vazio até haver sinais liquidados) |
