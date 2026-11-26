# Fases 7, 8 e 10 — Backend da plataforma (análise ao vivo, contas e administração)

- **Data:** 2026-11-25
- **Branch:** `plataforma-backend` (PR #14)
- **Plano:** `docs/superpowers/plans/2026-11-25-plataforma-backend.md`
- **Contrato implementado:** `docs/api/contrato-v1.md` (snapshot em `docs/api/openapi-v1.json`)

## Objetivo

Entregar o backend que o frontend (Fase 9) consome: contas e autenticação com assinatura checada no servidor, a API REST + WebSocket do contrato v1, o motor de análise ao vivo e a API de administração. Os sinais continuam em AGUARDAR: a Fase 6 não validou nenhuma combinação.

## O que foi construído

### Contas e autenticação (`sinais.contas`)

| Item | Como |
|---|---|
| Senhas | Argon2id (`argon2-cffi`, parâmetros RFC 9106 de baixa memória). Rehash automático se os parâmetros mudarem. E-mail inexistente gasta uma verificação de hash, para responder no mesmo tempo. |
| Sessão | Token opaco de 256 bits. O banco guarda só o SHA-256. Cookie `sinais_sessao` httpOnly, Secure, SameSite=Lax. Duração máxima 7 dias e ociosidade de 24 h (configuráveis). |
| CSRF | Double submit: cookie `sinais_csrf` (não httpOnly) igual ao cabeçalho `X-CSRF-Token` **e** igual ao CSRF da própria sessão (hash no banco). O CSRF de outra sessão não vale. |
| Limites | 20 tentativas de login por minuto por IP e 10 por e-mail → 429. Bloqueio progressivo: 5 falhas seguidas → 60 s, dobra a cada nova falha, teto de 30 min → 423. As chaves usam o hash do e-mail, então e-mail inexistente recebe as mesmas respostas (sem enumeração de contas). Contador no Redis (compartilhado entre processos). |
| 2FA | TOTP obrigatório para admin (`pyotp`, ±1 passo de 30 s). O mesmo código não vale duas vezes (último passo usado fica no usuário). Segredo TOTP cifrado com AES-GCM (`SINAIS_CHAVE_CIFRA`). `totp_necessario` só aparece com a senha certa. |
| Sessões simultâneas | 1 por conta por padrão (`SINAIS_SESSOES_SIMULTANEAS`): o login novo revoga a mais antiga. |
| Revogação | Logout, troca de senha (derruba as outras), bloqueio, desativação e redefinição de senha pelo admin revogam na hora. |
| Assinatura | Atual = a de maior `fim` já iniciada; `fim` é exclusivo. Checada no servidor em toda rota de dados e em cada `assinar` do WebSocket. Admin é dispensado (precisa inspecionar o produto). |
| Permissões | Recursos do plano: `ativos`, `expiracoes`, `modo_avancado`, `cursos`. Ativo fora do plano → 403 `ativo_nao_incluido`; `/api/sinais` só lista as expirações do plano; modo avançado exige o recurso. |
| Logs | `registros_acesso` (login, falha, bloqueio, limite, logout, troca de senha) com IP e user agent. `auditoria` de toda ação de admin com antes e depois, **sem** hash, senha temporária nem segredo TOTP (teste confere). |

### API (`sinais.api`, `python -m sinais.processos.api`)

Todas as rotas do contrato, conferidas pelo teste `test_todas_as_rotas_do_contrato_existem` e pelo snapshot `docs/api/openapi-v1.json` (o CI regenera e compara com `diff`):

- `/api/auth/login`, `/api/auth/logout`, `/api/eu`, `/api/eu/senha`, `/api/eu/preferencias`
- `/api/ativos`, `/api/candles` (1m direto; 3m…1w por `time_bucket` só com blocos completos), `/api/analise`, `/api/sinais`, `/api/sinais/historico`
- `/api/admin/usuarios` (GET/POST/PATCH `{id}`), `/api/admin/planos` (GET/POST/PATCH `{id}`), `/api/admin/assinaturas`, `/api/admin/acessos`, `/api/admin/auditoria`, `/api/admin/corretoras/exnova/payout` (GET/PUT), `/api/admin/qualidade`
- `/api/publico/estatisticas`
- `/api/ws`: canais `candles:SIMBOLO:TG`, `analise:SIMBOLO`, `sinais:SIMBOLO`. Uma leitura do Redis Streams por processo da API alimenta todos os assinantes (fila por cliente; cliente lento perde a mensagem mais antiga, não trava os outros). Sessão e assinatura checadas na conexão, em cada `assinar`, a cada `SINAIS_WS_VERIFICACAO_S` (5 s) e, sem ir ao banco, antes de cada envio. Fecha com **4401** (sessão revogada/expirada) e **4402** (assinatura vencida). Origem de outro site → 4403.

Erros sempre `{"erro": {"codigo", "mensagem"}}`, inclusive 404 de rota, 422 de validação e 500. Cabeçalhos: `nosniff`, `X-Frame-Options: DENY`, CSP `default-src 'none'`, `Cache-Control: no-store`, HSTS. Documentação interativa desligada por padrão (`SINAIS_DOCUMENTACAO=true` liga).

`/api/sinais` devolve AGUARDAR em todas as expirações, com `probabilidade: null` e `motivo: "Nenhum modelo validado para esta expiração"`, enquanto não houver campeão em `sinais.modelos.registro` (pasta `SINAIS_REGISTRO_MODELOS`).

### Motor de análise ao vivo (`python -m sinais.processos.motor_analise`)

1. Cria o grupo `motor_analise` em `candle.fechado` **antes** de carregar o banco (o que fechar durante a carga fica na fila).
2. Carrega os últimos `JANELA_AO_VIVO_1M` (18.000) minutos de cada símbolo do banco e publica a primeira análise.
3. A cada lote de eventos de 1m, lê do banco tudo o que falta até o candle do evento (o banco é a fonte da verdade e traz o volume agressor, que o evento não tem; lacunas de eventos se resolvem sozinhas) e calcula **uma vez por símbolo**.
4. `montar_snapshot` (fs-1, sem alteração) → `montar_analise` (puro) → guarda a última em `analise:ultima:SIMBOLO` e publica `analise.atualizada` (novo contrato em `sinais.eventos.contratos`).

Mapeamento do snapshot para a `Analise`: tendência = `est_tendencia` de 1m/5m/15m/1h (sem contexto → 0); força = ADX; ATR em preço = `ind_atr_rel × preço`; regiões, topo e fundo reconstruídos das distâncias em ATR; `macd_hist` em preço; último evento de estrutura = o CHoCH/BOS mais recente da janela. Valores sem histórico suficiente saem `null` (nunca NaN).

O `resumo` é montado por templates. O teste `test_resumo_nunca_inventa_numeros` extrai todo número de cada frase e confere que ele é um campo da própria `Analise`.

### Persistência

Migração `0002_contas`: `usuarios`, `configuracoes_usuario`, `sessoes`, `planos`, `assinaturas`, `pagamentos` (preparada para gateway), `registros_acesso`, `auditoria`, `corretoras`, `corretora_ativos` (seed Exnova + BTCUSDT/ETHUSDT) e `corretora_payouts` com **expiração**, faixa horária opcional e vigência (`valido_de`/`valido_ate`): o PUT do admin encerra o payout vigente e grava o novo, então o payout de qualquer instante passado continua consultável. Os mesmos casos de contrato (`tests/contrato/repositorio_contas.py`, `consultas_mercado.py`) rodam contra o dublê em memória e contra o PostgreSQL.

### Infra e comandos

- Compose: `api` (publicada só em `127.0.0.1:8000`, com healthcheck) e `motor_analise`.
- `python -m sinais.processos.criar_admin --email ...`: cria ou redefine o admin e imprime a URI `otpauth://` (senha por `SINAIS_ADMIN_SENHA` ou pelo terminal, nunca por argumento).
- `infra/fumaca.sh`: além da coleta, cria admin com 2FA, confere `totp_necessario`, cria plano e cliente pela API, confere 403 do cliente no admin, lê `/api/candles` (1m e 5m), espera a primeira `/api/analise`, confere 5 AGUARDAR em `/api/sinais` e o logout.

## Testes (saídas reais)

**Local** (sem FastAPI, argon2, pyotp, SQLAlchemy e Redis instalados; esses testes rodam no CI):

```
$ cd backend && python -m pytest -q
354 passed, 11 skipped in 17.49s
$ ruff format . && ruff check .     → All checks passed!
$ python -m mypy                    → Success: no issues found in 189 source files
```

**CI** (run 45649957322, commit `8e862f8`): backend, integracao, infra e fumaça verdes. Depois dos acréscimos pedidos pelo frontend, run 45757848951 (commit `29c7742`): os quatro jobs verdes, backend com 400 passed, 23 skipped e cobertura 97,42%, integracao com 23 passed.

```
backend:    394 passed, 23 skipped in 21.08s
            Required test coverage of 90% reached. Total coverage: 97.42%
            (core, logs, dados e contas; contas: servico 97%, admin 95%, demais 88–100%)
integracao: 23 passed in 18.47s
  test_api_integracao.py::test_matriz_de_autorizacao_com_banco_real PASSED
  test_api_integracao.py::test_usuario_a_nunca_le_dados_de_b PASSED
  test_api_integracao.py::test_vencimento_tira_rest_e_ws_na_hora PASSED
  test_api_integracao.py::test_revogacao_fecha_ws_4401 PASSED
  test_api_integracao.py::test_fan_out_do_redis_streams_ate_o_websocket PASSED
  test_repositorio_contas_pg.py (8 casos de contas + 3 de consultas) PASSED
fumaca:
  candles_1m=2882 candles_1s=172932 eventos_candle_fechado=137
  admin criado (URI TOTP emitida)
  admin sem TOTP: 401 totp_necessario
  admin entrou com 2FA
  plano 1 e cliente criados pelo admin
  cliente: assinatura ativa
  cliente em rota de admin: 403
  candles 1m: {"t":1795622340000,"o":"58398","h":"58398","l":"58344.01","c":"58344.01","v":"12.75678"}
  candles 5m: 3
  análise: t=1795622340000 preço=58344.01
    - Tendência de baixa em 15m
    - Preço a 0,53 ATR de uma resistência tocada 1 vez
    - Preço a 0,31 ATR de um suporte tocado 1 vez
    - Rompimento de estrutura para cima (BOS de alta)
  sinais: 5 expirações em AGUARDAR (Nenhum modelo validado para esta expiração)
  logout: sessão revogada
  Fumaça da API OK
```

### Matriz de autorização

18 rotas × 6 perfis (anônimo, assinatura vencida, sem assinatura, plano só BTC, plano completo, admin), em memória (`tests/unit/api/test_matriz_autorizacao.py`) e com PostgreSQL + Redis reais (`tests/integracao/test_api_integracao.py`). Resumo das regras confirmadas: sem sessão → 401; dados sem assinatura → 402; ativo fora do plano → 403; admin para cliente → 403; conta (`/api/eu`) com sessão mesmo vencida; público sempre 200.

### Problemas encontrados pelo CI e corrigidos

1. `Row.t` é atributo da própria linha no SQLAlchemy: `acessos` e `auditoria` liam a coluna `t` errada (falhou na integração; lido por `_mapping["t"]`).
2. Teste de limite de sessões criava três sessões no mesmo milissegundo; o desempate era aleatório.
3. O cliente de teste do Starlette cancela a conexão WS no fechamento; a conexão agora cancela as próprias tarefas internas (nenhuma tarefa órfã também no desligamento real do servidor).

## Auditoria

Revisão do autor sobre o branch inteiro (sem revisor independente nesta sessão: uma revisão por outra pessoa ou agente antes do merge é recomendada).

| Ponto | Resultado |
|---|---|
| Assinatura só no navegador (antiobjetivo §2) | Não: checada no servidor em toda rota de dados e em cada `assinar`; vencimento derruba REST e WS na hora (teste de integração). |
| Usuário A lendo dados de B | Nenhuma rota de cliente recebe id de usuário; os dados vêm do usuário da sessão. CSRF de A não vale na sessão de B. Teste com banco real. |
| Segredos em log | Logs de acesso guardam evento, usuário, IP e user agent. Auditoria sem hash/senha/TOTP (teste). Configuração nomeia a variável e nunca o valor. Erro 500 loga só o tipo da exceção. |
| Enumeração de contas | Mesma resposta, mesmo bloqueio e mesmo custo de hash para e-mail inexistente (teste). |
| WebSocket entre sites (CSWSH) | Origin precisa ser o próprio host ou estar em `SINAIS_ORIGENS_PERMITIDAS`. |
| IP atrás de proxy | `SINAIS_PROXIES_CONFIAVEIS` (CIDRs): o `X-Forwarded-For` só é lido de proxies confiáveis, da direita para a esquerda, pulando os proxies. Ver "Passe de correções". |
| Números inventados no resumo | Impossível por construção e verificado por teste em cinco cenários. |
| Look-ahead na análise ao vivo | O motor usa o mesmo `montar_snapshot` do laboratório sobre candles fechados do banco. |

Pendências menores registradas (não bloqueiam): a última análise não expira se o motor parar (o campo `t` mostra a idade); sem CAPTCHA após falhas repetidas (bloqueio progressivo cobre a força bruta); limite de requisições só no login; admin pode criar usuário em plano inativo; lote do motor que falha só é relido no reinício (o evento seguinte recarrega do banco).

## Decisões (onde o contrato é omisso)

- `Analise.preco` é string decimal (convenção "preços como string"); preços de regiões e topo/fundo são `number` (valores calculados). `Analise.t` é a abertura do último candle de 1m fechado (o mesmo `t` de `/api/candles`).
- Campos numéricos da `Analise` sem histórico suficiente saem `null`.
- `/api/eu`, `/api/eu/senha` e `/api/eu/preferencias` exigem sessão, não assinatura: o usuário vencido precisa ver o status e trocar a senha.
- Admin é dispensado de assinatura nas rotas de dados.
- Com campeão no registro e sem motor de sinais, `/api/sinais` continua AGUARDAR com `motivo: "Modelo validado, mas o motor de sinais ao vivo ainda não está ativo"` e `modelo` preenchido. Nunca aparece probabilidade que não saiu do motor validado.
- `/api/sinais/historico` e `/api/publico/estatisticas` devolvem `[]`: ainda não existem sinais gravados (motor de sinais e liquidador ficam para a continuação da Fase 7).
- Canal `candles` só envia `fechado: true`: o coletor ainda não publica o candle em formação.
- `/api/candles`: `ate` é exclusivo (abertura `< ate`), padrão = agora; a janela de `limite` períodos termina no último dado existente.
- WebSocket: erro por canal vai como `{"canal", "erro": {codigo, mensagem}}`; mensagem inválida como `{"erro": ...}`; até 20 canais por conexão.
- Admin: `PATCH /api/admin/usuarios/{id}` e `PATCH /api/admin/planos/{id}`; `plano` na criação de usuário aceita id ou nome; e-mail ou nome de plano repetido → 409; a API cria só clientes (admins só pelo `criar_admin`, que provisiona o TOTP).
- `fastapi==0.165.0` (versão atual resolvida no CI; o ADR-03 citava a série 0.14x — a regra de fixar com `==` foi mantida).

## Acréscimos pedidos pelo frontend (compatíveis com a v1)

Pedidos em `docs/fases/fase-09-frontend.md` §3 (branch `plataforma-frontend`), implementados como campos e rotas a mais, sem remover nada:

1. `Usuario.layout: object` em `GET /api/eu` (e nas demais respostas com `Usuario`): o que foi salvo por `PATCH /api/eu/preferencias`.
2. `Sinal.tolerancia_preco: number|null` (k × ATR, em preço) e `Sinal.preco_referencia: string|null` (design §12.6); nulos em AGUARDAR.
3. Formatos fixados: `UsuarioAdmin = Usuario + {status, criado_em}`; `Acesso = {id, usuario_id, email, evento, ip, user_agent, t, ts}`; `Auditoria = {id, admin_id, admin_email, acao, alvo, antes, depois, t, ts}`; `EventoQualidade = {simbolo, intervalo, inicio, fim, tipo, detalhes}`; `EstatisticaPublica = {simbolo, expiracao, n, taxa, inicio, fim}`. `ts` repete `t` (nome usado pelo frontend).
4. `GET /api/eu`, `POST /api/eu/senha` e `POST /api/auth/logout` funcionam com assinatura vencida (só 401 sem sessão, nunca 402). Já era assim; agora há teste específico.
5. `PATCH /api/admin/planos` com o plano inteiro (incluindo `id`) no corpo, além de `PATCH /api/admin/planos/{id}`; `id` do corpo diferente do da rota → 422.
6. Payout sempre em fração (0,86), `0 < payout <= 1`.

## Passe de correções da revisão de segurança (PR #14, base `1cea77e`)

Cada correção tem teste que falhou antes (unitário com dublê que intercala as chamadas, ou integração com PostgreSQL/Redis reais).

| # | Problema | Correção | Teste |
|---|---|---|---|
| 1 | Escrita da linha inteira com fotografia antiga ressuscitava sessão revogada, desbloqueava usuário ou desfazia troca de senha; TOTP reusado em paralelo; dois logins simultâneos com limite 1 | `tocar_sessao`/`revogar_sessao` com `WHERE revogada_em IS NULL`; `atualizar_usuario` só com as colunas pedidas; `atualizar_preferencias`; `registrar_passo_totp` condicional (`totp_ultimo_passo < :p`, exatamente 1 linha); limite de sessões aplicado **depois** de gravar a nova, com ordem determinística (`criada_em`, `seq`) | `test_concorrencia.py` (5 casos), contratos de repositório, `test_concorrencia_real_no_postgres` |
| 2 | Argon2 no laço de eventos | `asyncio.to_thread` + semáforo (`hash_paralelo`, padrão 4) | `test_hash_de_senha_roda_fora_do_laco_e_com_limite_de_paralelismo` |
| 3 | Bloqueio só por e-mail deixava qualquer um travar um admin | Bloqueio progressivo por (e-mail, IP) + teto global por e-mail (50 falhas/h → 15 min), sem enumeração | `test_atacante_de_outro_ip_nao_bloqueia_o_dono_da_conta`, `test_teto_global_por_email_...` |
| 4 | WS mantinha canal de ativo que saiu do plano | A cada verificação periódica, cancela o canal e envia o quadro de erro | `test_plano_reduzido_durante_a_conexao_cancela_o_canal_do_ativo` |
| 5 | Implantação atrás de Next/nginx | `SINAIS_PROXIES_CONFIAVEIS` (CIDRs, XFF pela direita); `Origin` do WS só por `SINAIS_ORIGENS_PERMITIDAS` (e `X-Forwarded-Host` só de proxy confiável); com `SINAIS_AMBIENTE=prod` as origens são obrigatórias e a chave do `.env.example` é recusada; padrão de dev aceita `http://localhost:3000` | `test_ip_do_cliente_anda_no_x_forwarded_for_...`, `test_origem_permitida_...`, `test_producao_exige_origens_...` |
| 6 | Fonte de eventos do WS morria calada; `campeao.json` malformado | Tarefas de fundo supervisionadas (reinício com log); entrada ruim do stream registrada e pulada; registro malformado → AGUARDAR com log | `test_supervisor_...`, `test_entrada_ruim_no_stream_...`, `test_campeao_malformado_cai_para_aguardar` |
| 7 | Motor travava num lote envenenado | Evento malformado → fila morta `candle.fechado.mortos` + ACK; falha de cálculo só reenvia o símbolo afetado; XPENDING/XCLAIM com no máximo 5 entregas; consumidor por `SINAIS_CONSUMIDOR` ou host | `test_evento_envenenado_...`, `test_falha_de_calculo_...`, `test_pendentes_...`, `test_nome_do_consumidor_...` |
| 8 | Admin não conseguia encerrar assinatura antes do fim | `POST /api/admin/assinaturas/{id}/encerrar` (auditado, vale na hora) | `test_encerrar_assinatura_...`, `test_admin_encerra_assinatura_...` |

Menores corrigidos: cabeçalhos de segurança também no 500; AES-GCM com dado associado `usuario:{id}` e prefixo de chave `k1:`; e-mail tomado entre checagem e gravação → 409; limite de 5 trocas de senha por sessão em 15 min (429); volume do registro de modelos no Compose; resumo diz "Sem dados de tendência em …" quando falta histórico e nunca escreve distância negativa; rótulos de expiração num lugar só (`core.dominio.ROTULOS_EXPIRACAO`); layout aninhado demais e corpo ilegível → 422; candles de 3m a 1w com os minutos disponíveis e só períodos fechados (uma lacuna não some com o 1d ou 1w inteiro); migração com `ondelete` explícito, CHECK de expiração e vigência, índice único do payout vigente, índice de expiração das sessões e teste de downgrade. CI verde em `de91891`.

## Gráfico ao vivo tick a tick (1m a 1w)

- `processos/ticks_binance.py` (serviço `ticks`): stream combinado `<simbolo>@aggTrade` com o mesmo consumidor do coletor (reconexão com backoff, renovação antes de 24 h). Publica cada negócio no Redis Pub/Sub `ticks:{SIMBOLO}` (não grava nada; os candles persistidos continuam vindo só dos klines fechados). Em toda (re)conexão, antes de ler o stream, republica pelo REST (`/api/v3/aggTrades`) os negócios do minuto atual.
- `dados/vela_formacao.py` (puro): para cada tempo gráfico, período atual = minutos de 1m oficiais (do banco, desde o início da semana) + negócios dos minutos abertos, cada um no minuto do seu `T`; primeiro/último pelo id do aggTrade (ordem de chegada não importa), repetidos descartados; o 1m oficial substitui o parcial e negócios com `T` anterior ao fim dele são descartados; lacuna de fechamentos → recarga do banco.
- `api/velas.py`: publica `candles:SIMBOLO:TG` com `fechado: false` e `preco:SIMBOLO`, no máximo uma mensagem por canal a cada 100 ms (último valor vence), só nos canais com assinantes; foto imediata na assinatura. O `fechado: true` continua saindo do `candle.fechado`.

Prova "igual à Binance" (job `ticks` do CI, run 45816490550, 3 minutos reais, igualdade exata de `Decimal`):

```
BTCUSDT: 2500 aggTrades, 4 velas, igual=True
ETHUSDT: 925 aggTrades, 4 velas, igual=True
| BTCUSDT | 1m | 1795694820000 | 60841.98/60864.28/60826.00/60832.30/6.90410 | (igual na Binance) | sim |
| BTCUSDT | 1m | 1795694880000 | 60832.30/60832.31/60791.54/60800.00/10.11403 | (igual) | sim |
| BTCUSDT | 1m | 1795694940000 | 60800.01/60800.12/60772.33/60794.19/9.20856 | (igual) | sim |
| BTCUSDT | 5m | 1795694700000 | 60875.43/60875.43/60772.33/60794.19/39.30907 | (igual) | sim |
| ETHUSDT | 1m | 1795694820000 | 1705.98/1706.96/1705.46/1705.88/90.954 | (igual) | sim |
| ETHUSDT | 1m | 1795694880000 | 1705.87/1705.88/1704.55/1704.67/43.3935 | (igual) | sim |
| ETHUSDT | 1m | 1795694940000 | 1704.67/1706.11/1704.06/1706.11/204.4395 | (igual) | sim |
| ETHUSDT | 5m | 1795694700000 | 1707.49/1707.49/1704.06/1706.11/466.6057 | (igual) | sim |
{"igual": true}
```

Na mesma run: backend 459 passed, 31 skipped (cobertura 97,28%), integracao 31 passed, fumaça com "ticks recebidos em 15 s: 157". Testes unitários: negócio exatamente na abertura, fora de ordem e repetido, ressincronização sem duplicar, reconciliação, lacuna com recarga, virada da semana (segunda 00:00 UTC), vazão coalescida, foto na assinatura.

## Acréscimos ao contrato (texto proposto)

- **WebSocket, quadros de erro:** `{"canal": "<canal>", "erro": {"codigo", "mensagem"}}` (ex.: `ativo_nao_incluido`, `limite_canais`) e `{"erro": {"codigo": "mensagem_invalida", "mensagem"}}`. O frontend pode ignorar quadros com `erro`.
- **WebSocket, fechamento:** 4401 sessão revogada/expirada, 4402 assinatura vencida, **4403** origem não permitida.
- **`candles:SIMB:TG`:** `{t, o, h, l, c, v, fechado}`; `fechado: false` = vela em formação, tick a tick, no máximo 1 mensagem por canal a cada 100 ms (coalescida, último valor vence); `fechado: true` no fechamento oficial. Ao assinar, uma foto imediata da vela em formação (se houver negócio).
- **`preco:SIMB`** (novo): `{preco: string decimal, t: int ms}`, mesmas regras de vazão, foto na assinatura e checagem de plano.
- **`POST /api/admin/assinaturas/{id}/encerrar`** → `200 Assinatura` com `fim = agora` (nunca estica uma já encerrada); `404 assinatura_inexistente`.
- **Códigos:** `409 email_em_uso`, `409 plano_existente`, `404 ativo_desconhecido`, `404 analise_indisponivel`, `404 usuario_inexistente`, `404 plano_inexistente`, `404 assinatura_inexistente`, `429 muitas_tentativas` também em `POST /api/eu/senha`.
- **Candles de 3m a 1w:** agregados com os minutos disponíveis, só períodos fechados.

## Não feito nesta entrega

- Motor de sinais (decisão por expiração), liquidador e monitor da Fase 7: dependem de um campeão aprovado.
- Candle em formação no WebSocket: exige o coletor publicar um evento parcial (fora do escopo deste branch).
- CAPTCHA, limite geral de requisições por sessão, exportação/exclusão de dados (LGPD) e testes de carga ficam para a Fase 11.
