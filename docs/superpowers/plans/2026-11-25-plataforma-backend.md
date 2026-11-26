# Plataforma — backend (Fases 7, 8 e 10) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Contas e autenticação, API FastAPI completa do contrato v1 (REST + WebSocket), motor de análise ao vivo e API de administração, com testes de autorização no CI.

**Architecture:** Regras de negócio em módulos puros (`sinais.contas`, `sinais.api.esquemas`, `montar_analise`) testados localmente com dublês em memória. Adaptadores finos (FastAPI, SQLAlchemy Core, Redis, argon2, pyotp) testados no CI: rotas com `TestClient` + dublês no job `backend`, PostgreSQL/Redis reais no job `integracao`. Um mesmo conjunto de casos de contrato roda contra o repositório em memória (local) e o PostgreSQL (CI).

**Tech Stack:** Python 3.13, FastAPI 0.14x (fixado com `==`), Uvicorn, Pydantic v2, SQLAlchemy 2 Core + Alembic, Redis Streams, argon2-cffi, pyotp, cryptography (AES-GCM do segredo TOTP).

**Spec:** `docs/superpowers/specs/2026-11-25-plataforma-sinais-design.md` (§7 ADR-03/05/06/10/12, §9–§11, §14, §15, §17 fases 7–10) e `docs/api/contrato-v1.md` (fonte da verdade das rotas).

## Global Constraints

- Código, docs, commits e PR em português do Brasil; identificadores em português.
- Erros sempre `{"erro": {"codigo": "...", "mensagem": "..."}}`; 401 sem sessão, 402 assinatura vencida/inexistente, 403 sem permissão, 422 validação, 423 conta bloqueada, 429 limite.
- Instantes em ms UTC (`int`); preços de candle como string decimal; valores de análise como `number`.
- Cookie `sinais_sessao` httpOnly/Secure/SameSite=Lax; `sinais_csrf` não httpOnly; mutações exigem `X-CSRF-Token` = cookie.
- Sessão e assinatura checadas no servidor em toda rota de dados e em cada `assinar` do WebSocket; WS fecha com 4401 (sessão revogada) e 4402 (assinatura vencida).
- Nenhum segredo (senha, hash, token, segredo TOTP, código TOTP) em log, resposta ou auditoria.
- Não tocar `sinais/{modelos,backtest,features}`, `frontend/`, `docs/api/contrato-v1.md`, `docs/PROGRESSO.md`.
- `resumo` da análise só por template a partir dos números da própria `Analise`.

## Review Focus

1. Usuário com sessão válida cuja assinatura vence durante a conexão WS → fechado com 4402 em até `ws_verificacao_s`, e o próximo REST dá 402 (teste no Task 6 e integração).
2. E-mail inexistente vs. senha errada → mesma resposta 401 e o mesmo bloqueio progressivo (sem enumeração) (Task 2).
3. Admin com senha certa e TOTP reutilizado (mesmo passo de 30 s) → 401 `totp_invalido` (Task 2).
4. Histórico curto no banco (menos que `JANELA_AO_VIVO_1M`, ex.: CI com 1 dia) → análise montada sem NaN no JSON (campos sem valor viram `null`, tendência sem contexto vira 0) (Task 4).
5. Bloqueio de usuário pelo admin → todas as sessões dele revogadas na hora (REST 401, WS 4401) (Task 3).

---

### Task 1: Domínio de contas e repositório (memória + contrato)

**Files:**
- Create: `backend/src/sinais/contas/{__init__,modelos,repositorio,memoria,seguranca}.py`
- Create: `backend/tests/contrato/repositorio_contas.py`, `backend/tests/unit/contas/test_repositorio_memoria.py`, `backend/tests/unit/contas/test_seguranca.py`

**Interfaces:**
- Produces: dataclasses `Usuario, Plano, Recursos, Assinatura, Sessao, RegistroAcesso, RegistroAuditoria, ItemPayout`; enums `Papel(cliente, admin)`, `StatusUsuario(ativo, bloqueado, desativado)`, `Modo(essencial, avancado)`; `Protocol RepositorioContas` (async: usuários, sessões, planos, assinaturas, acessos, auditoria, payouts); `RepositorioContasMemoria`; `gerar_token() -> str`, `hash_token(str) -> str` (SHA-256 hex), `iguais(a, b) -> bool` (tempo constante), `CifraSegredos(chave: bytes)` com `cifrar/decifrar` (AES-GCM).
- Assinatura atual = maior `fim` entre as com `inicio <= agora`.

- [ ] Casos de contrato (`CASOS`) escritos e falhando contra a memória; implementar; verdes; commit.

### Task 2: Serviço de contas (login, sessões, CSRF, bloqueio, TOTP, assinatura)

**Files:**
- Create: `backend/src/sinais/contas/{senhas,totp,limites,servico,autorizacao}.py`
- Test: `backend/tests/unit/contas/test_servico_login.py`, `test_servico_sessoes.py`, `test_limites.py`, `test_autorizacao.py`, `test_adaptadores.py` (argon2/pyotp com `importorskip`)

**Interfaces:**
- `Protocol Hasher {gerar, verificar, precisa_rehash}`; `HasherArgon2` (argon2id, perfil RFC 9106 baixo-memória).
- `Protocol VerificadorTotp {novo_segredo, passo_valido(segredo, codigo, agora_ms) -> int|None, uri(segredo, email)}`; `TotpPyotp` (janela ±1 passo).
- `Protocol ContadorLimites {incrementar(chave, janela_s) -> int, zerar(chave)}`; `ContadorMemoria(relogio)`.
- `PoliticaLogin`: 5 falhas seguidas → bloqueio de 60 s, dobra a cada falha extra, teto 1800 s; 20 tentativas/min por IP e 10/min por e-mail → 429. Chaves por hash do e-mail (vale para e-mail inexistente).
- `ServicoContas.login(email, senha, totp, ip, ua) -> ResultadoLogin(usuario, token, csrf)`; erros `ErroConta(status, codigo, mensagem)`. Limite de sessões (padrão 1): login novo revoga as antigas.
- `ServicoContas.autenticar(token, agora) -> Contexto(usuario, sessao, assinatura, plano)` (401 sem/expirada/revogada); `exigir_assinatura(ctx)` (402; admin dispensado); `verificar_csrf(ctx, cabecalho, cookie)` (403 `csrf_invalido`).
- `autorizacao.pode_ver_ativo(ctx, simbolo)`, `expiracoes_permitidas(ctx)`, `pode_modo_avancado(ctx)`.

- [ ] Testes por comportamento (falha antes), implementação, verdes, commit.

### Task 3: Operações de admin e auditoria

**Files:** Modify `contas/servico.py` (classe `ServicoAdmin`); Test `tests/unit/contas/test_servico_admin.py`
- Criar/editar/bloquear/desativar usuário (bloqueio e desativação revogam sessões), planos, assinaturas (criar/renovar), payout Exnova (substitui o vigente e fecha o anterior com `valido_ate`), listas de acessos e auditoria. Toda ação grava `auditoria(admin_id, acao, alvo, antes, depois)` sem campos secretos.

### Task 4: Análise ao vivo pura (`montar_analise`)

**Files:** Create `backend/src/sinais/api/esquemas.py` (modelos Pydantic do contrato), `backend/src/sinais/processos/motor_analise.py` (`montar_analise(simbolo, snapshot) -> Analise`, `montar_resumo(Analise) -> list[str]`, `JanelaSimbolo`, `MotorAnalise`); Test `tests/unit/processos/test_motor_analise.py`
- Lê só a última linha do snapshot fs-1 (e as colunas `est_bos/est_choch` para o último evento). ATR = `ind_atr_rel × c`; `macd_hist` em preço = `ind_macd_hist × ATR`; topo/fundo e preços das regiões a partir das distâncias em ATR. NaN → `null`; tendência sem contexto → 0.
- Resumo: frases fixas com números formatados com vírgula decimal, todos presentes na `Analise` (teste confere cada número do texto contra os campos).
- `MotorAnalise.processar(evento)`: ignora repetidos, recarrega a janela em lacuna, calcula com `montar_snapshot` e publica `analise.atualizada` + guarda a última por símbolo.

### Task 5: Persistência PostgreSQL (migração 0002 + repositórios)

**Files:** Create `backend/migracoes/versions/0002_contas.py`, `backend/src/sinais/persistencia/{tabelas_contas,repositorio_contas_pg,consultas_mercado}.py`; Test `tests/integracao/test_repositorio_contas_pg.py` (roda `CASOS` da Task 1), `tests/unit/persistencia/test_consultas_memoria.py`
- Tabelas: `usuarios, sessoes, planos, assinaturas, pagamentos, registros_acesso, auditoria, configuracoes_usuario, corretoras, corretora_ativos, corretora_payouts (expiracao_s, hora_inicio?, hora_fim?, payout, valido_de, valido_ate)`; seed Exnova + BTCUSDT/ETHUSDT.
- `ConsultasMercado.candles(simbolo, tg, ate, limite)` (1m direto; maiores com `time_bucket` e `HAVING count(*) = minutos`) e `qualidade_recentes(limite)`.

### Task 6: API FastAPI (REST + WS) e OpenAPI

**Files:** Create `backend/src/sinais/api/{app,config,erros,dependencias,ws,analises}.py`, `api/rotas/{auth,eu,mercado,admin,publico}.py`, `backend/src/sinais/processos/api.py`, `docs/api/openapi-v1.json`; Test `tests/unit/api/test_rotas.py`, `test_ws.py`, `test_matriz_autorizacao.py` (`importorskip("fastapi")`), `tests/unit/api/test_ws_canais.py` (puro), `test_openapi.py` (snapshot)
- `criar_app(servicos: Servicos) -> FastAPI`; `/api/sinais` = AGUARDAR "Nenhum modelo validado para esta expiração" sem campeão no `Registro`.
- WS: `Distribuidor` (fan-out por canal) alimentado por leitor XREAD de `candle.fechado` e `analise.atualizada`; recheca sessão/assinatura a cada `ws_verificacao_s` e em cada `assinar`.

### Task 7: Processos, infra, fumaça e CI

**Files:** Create `processos/criar_admin.py`; Modify `infra/docker-compose.yml`, `infra/fumaca.sh`, `.env.example`, `.github/workflows/ci.yml`, `backend/pyproject.toml`; Test `tests/integracao/test_api_integracao.py` (matriz papel × plano × rota, A≠B, vencimento REST+WS com PG/Redis reais).

### Task 8: Documentação

**Files:** Create `docs/fases/fase-07-08-10-backend.md` com o que foi feito, saídas reais dos testes e auditoria.
