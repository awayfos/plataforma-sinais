# Fase 2 — Estrutura Inicial: Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar o monorepo com o pacote `sinais` (núcleo de domínio, relógio, calendário de mercado, configuração e logs estruturados), a infraestrutura Docker Compose (PostgreSQL+TimescaleDB e Redis) e o pipeline de CI.

**Architecture:** Pacote Python `sinais` em `backend/src/` com layout src, gerenciado por `uv`. A Fase 2 entrega só `sinais.core` (sem I/O) e `sinais.logs`, mais a infraestrutura. Tudo em UTC com milissegundos inteiros (ADR-13). O relógio é injetável para que os testes controlem o tempo.

**Tech Stack:** Python 3.13, pytest, mypy (strict), ruff, pydantic v2, stdlib `logging` + `zoneinfo`, Docker Compose, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-25-plataforma-sinais-design.md` (§7.2, §8, §9 `core`, §14, §17 Fase 2)

## Global Constraints

- Python `>=3.13,<3.14`. Pacote `sinais`, layout `backend/src/sinais/`.
- Todo instante é `int` em milissegundos desde a época Unix, UTC. Nenhum `datetime` ingênuo cruza fronteiras de módulo.
- `sinais.core` não faz I/O (rede, disco, banco).
- mypy `--strict` sem erros. Cobertura de `sinais.core` ≥ 90%.
- Semana dos candles começa segunda 00:00 UTC, como na Binance (design §9 `dados.candles`).
- Tempos gráficos da plataforma: 1m, 3m, 5m, 15m, 30m, 1h, 4h, 1d, 1w (design §6).
- Expirações da V1: 1, 5, 15 e 30 min e 1 h (design §6).
- Ativos da V1: BTCUSDT e ETHUSDT, classe cripto, 24/7 (design §6).
- Segredos nunca no repositório. Só `.env.example` com valores fictícios.
- Logs em JSON, uma linha por evento, com `ts` (ISO 8601 UTC), `nivel`, `evento`, `logger` e campos extras (ADR-14).

## Review Focus

1. Instante exatamente na fronteira de um candle (ex.: 00:05:00.000 em 5m): deve abrir o novo candle, não pertencer ao anterior. Teste em Task 3.
2. Instante negativo ou anterior a 1970, ou valor `float`: deve ser rejeitado com erro claro, não truncado em silêncio. Teste em Task 2.
3. Semana: um domingo 23:59 UTC pertence à semana iniciada na segunda anterior. Teste em Task 3.
4. Variável de ambiente obrigatória ausente ou malformada: a configuração falha na inicialização com mensagem que nomeia a variável, sem vazar o valor de segredos. Teste em Task 5.
5. Log com exceção: o traceback vai no campo `excecao` do JSON, sem quebrar a linha única. Teste em Task 6.

---

### Task 1: Esqueleto do repositório e ferramentas

**Files:**
- Create: `.gitignore`, `README.md`, `backend/pyproject.toml`, `backend/src/sinais/__init__.py`, `backend/src/sinais/py.typed`, `backend/tests/__init__.py`, `backend/tests/unit/__init__.py`, `backend/tests/unit/test_pacote.py`

**Interfaces:**
- Produces: pacote importável `sinais` com `sinais.__version__: str = "0.1.0"`.

- [ ] **Step 1: Write the failing test** — `test_pacote_importa_com_versao`: `import sinais; assert sinais.__version__ == "0.1.0"`.
- [ ] **Step 2: Run** `cd backend && PYTHONPATH=src python -m pytest tests -q` → FAIL (`ModuleNotFoundError`).
- [ ] **Step 3: Create the files.** `pyproject.toml`: projeto `sinais`, `requires-python = ">=3.13,<3.14"`, build `hatchling`, dependências `pydantic>=2.13,<3`; grupo `dev`: `pytest`, `pytest-cov`, `mypy`, `ruff`, `hypothesis`. `[tool.pytest.ini_options]` com `pythonpath = ["src"]`, `testpaths = ["tests"]`. `[tool.mypy]` com `strict = true`, `files = ["src", "tests"]`. `[tool.ruff]` com `line-length = 100`, `target-version = "py313"`, regras `E,F,I,B,UP,S,N`. `.gitignore`: `.venv/`, `__pycache__/`, `.env`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`, `node_modules/`, `.coverage`.
- [ ] **Step 4: Run** `cd backend && python -m pytest -q` → PASS; `python -m mypy` → `Success`.
- [ ] **Step 5: Commit** `chore: esqueleto do repositório e ferramentas`.

### Task 2: Tempo em UTC e relógio injetável

**Files:**
- Create: `backend/src/sinais/core/__init__.py`, `backend/src/sinais/core/tempo.py`
- Test: `backend/tests/unit/core/test_tempo.py` (+ `__init__.py`)

**Interfaces:**
- Produces:
  - `type InstanteMs = int`
  - `def validar_instante(ms: object) -> InstanteMs` — aceita só `int` (não `bool`) ≥ 0; senão `ValueError`.
  - `def de_datetime(dt: datetime) -> InstanteMs` — exige `tzinfo`; `ValueError` para ingênuo.
  - `def para_datetime(ms: InstanteMs) -> datetime` — UTC.
  - `def para_iso(ms: InstanteMs) -> str` — `"2026-11-25T03:00:00.000Z"`.
  - `class Relogio(Protocol): def agora_ms(self) -> InstanteMs`
  - `class RelogioSistema` (usa `time.time_ns() // 1_000_000`)
  - `class RelogioFixo(inicio_ms: InstanteMs)` com `avancar(ms: int) -> None` e `definir(ms: InstanteMs) -> None`

- [ ] **Step 1: Write the failing tests:**
  - `test_de_datetime_utc`: `de_datetime(datetime(2026,11,25,3,0,tzinfo=UTC)) == 1795575600000`
  - `test_de_datetime_com_fuso_converte`: 00:00 em `ZoneInfo("America/Sao_Paulo")` em 25/11/2026 == `1795575600000`
  - `test_de_datetime_ingenuo_rejeita`: `pytest.raises(ValueError)`
  - `test_para_iso`: `para_iso(1795575600123) == "2026-11-25T03:00:00.123Z"`
  - `test_ida_e_volta`: `de_datetime(para_datetime(x)) == x` para `x` em `[0, 1, 1795575600123]`
  - `test_validar_instante_rejeita` parametrizado: `-1`, `1.5`, `True`, `"10"` → `ValueError`
  - `test_relogio_fixo_avanca`: `r = RelogioFixo(1000); r.avancar(500); r.agora_ms() == 1500`
  - `test_relogio_sistema_proximo_de_time`: `abs(RelogioSistema().agora_ms() - int(time.time()*1000)) < 1000`
- [ ] **Step 2: Run** `python -m pytest tests/unit/core/test_tempo.py -q` → FAIL.
- [ ] **Step 3: Implement** `sinais/core/tempo.py` com as assinaturas acima.
- [ ] **Step 4: Run** → PASS; `python -m mypy` → `Success`.
- [ ] **Step 5: Commit** `feat(core): tempo em UTC e relógio injetável`.

### Task 3: Tipos de domínio e alinhamento de candles

**Files:**
- Create: `backend/src/sinais/core/dominio.py`
- Test: `backend/tests/unit/core/test_dominio.py`

**Interfaces:**
- Consumes: `InstanteMs`, `validar_instante` (Task 2).
- Produces:
  - `class TempoGrafico(StrEnum)`: `M1="1m", M3="3m", M5="5m", M15="15m", M30="30m", H1="1h", H4="4h", D1="1d", W1="1w"`, com a propriedade `duracao_ms: int`.
  - `def abertura_candle(instante: InstanteMs, tg: TempoGrafico) -> InstanteMs` — para `W1`, segunda 00:00 UTC; para os demais, `instante - instante % duracao_ms`.
  - `def fechamento_candle(instante, tg) -> InstanteMs` = abertura + duração (exclusivo).
  - `class Expiracao(IntEnum)` em segundos: `M1=60, M5=300, M15=900, M30=1800, H1=3600`.
  - `class Direcao(StrEnum)`: `COMPRA="BUY", VENDA="SELL", AGUARDAR="WAIT"`.
  - `class ClasseAtivo(StrEnum)`: `CRIPTO, FOREX, METAL, ACAO`.
  - `@dataclass(frozen=True, slots=True) class Ativo`: `simbolo: str`, `classe: ClasseAtivo`, `provedor: str`, `simbolo_provedor: str`, `precisao_preco: int`. `__post_init__` valida símbolo não vazio e em maiúsculas, `precisao_preco` de 0 a 12.
  - `ATIVOS_V1: tuple[Ativo, ...]` com BTCUSDT e ETHUSDT (provedor `"binance"`, precisão 2).

- [ ] **Step 1: Write the failing tests:**
  - `test_duracoes`: `M1.duracao_ms == 60_000`, `H4 == 14_400_000`, `D1 == 86_400_000`, `W1 == 604_800_000`
  - `test_abertura_na_fronteira_exata`: `abertura_candle(de_datetime(00:05:00 UTC), M5)` == 00:05:00 (Review Focus 1)
  - `test_abertura_um_ms_antes`: 00:04:59.999 → 00:00:00 em M5
  - `test_semana_comeca_segunda`: quarta 25/11/2026 12:00 UTC → segunda 23/11/2026 00:00 UTC
  - `test_domingo_fim_pertence_semana_anterior`: domingo 29/11/2026 23:59 UTC → segunda 23/11/2026 00:00 UTC (Review Focus 3)
  - `test_fechamento_exclusivo`: `fechamento_candle(x, M1) == abertura_candle(x, M1) + 60_000`
  - `test_ativo_invalido` parametrizado: símbolo `""`, `"btcusdt"`, precisão `-1` → `ValueError`
  - `test_ativos_v1`: símbolos == `("BTCUSDT", "ETHUSDT")`, todos `ClasseAtivo.CRIPTO`
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** `sinais/core/dominio.py`.
- [ ] **Step 4: Run** → PASS; mypy `Success`.
- [ ] **Step 5: Commit** `feat(core): tipos de domínio e alinhamento de candles`.

### Task 4: Calendário de mercado

**Files:**
- Create: `backend/src/sinais/core/calendario.py`
- Test: `backend/tests/unit/core/test_calendario.py`

**Interfaces:**
- Consumes: `InstanteMs`, `Ativo`, `ClasseAtivo`.
- Produces:
  - `class CalendarioMercado(Protocol)`: `def aberto(self, instante: InstanteMs) -> bool`; `def proxima_abertura(self, instante: InstanteMs) -> InstanteMs | None`.
  - `class Calendario24x7` — sempre aberto; `proxima_abertura` devolve o próprio instante.
  - `class CalendarioSemanalFx` — aberto de domingo 17:00 a sexta 17:00 no fuso `America/New_York` (horário de verão tratado por `zoneinfo`). Preparado para forex e metais, não usado na V1.
  - `def calendario_para(ativo: Ativo) -> CalendarioMercado` — `CRIPTO` → 24x7; `FOREX`/`METAL` → semanal FX; `ACAO` → `NotImplementedError("calendário de ações: V1.1")`.

- [ ] **Step 1: Write the failing tests:**
  - `test_cripto_sempre_aberto`: aberto em sábado 28/11/2026 03:00 UTC
  - `test_fx_fechado_sabado`: `CalendarioSemanalFx().aberto(sábado 12:00 UTC) is False`
  - `test_fx_abre_domingo_17h_ny_inverno`: domingo 29/11/2026 21:59:59.999 UTC fechado; 22:00:00.000 UTC aberto (EST, UTC−5)
  - `test_fx_abre_domingo_17h_ny_verao`: domingo 07/06/2026 20:59:59.999 UTC fechado; 21:00 UTC aberto (EDT, UTC−4)
  - `test_fx_fecha_sexta_17h_ny`: sexta 27/11/2026 21:59 UTC aberto; 22:00 UTC fechado
  - `test_proxima_abertura_fx`: de sábado 28/11 12:00 UTC → domingo 29/11 22:00 UTC
  - `test_acao_nao_implementado`: `pytest.raises(NotImplementedError)`
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.** O semanal FX converte o instante para `America/New_York` e compara dia da semana e hora local. Não usa offsets fixos.
- [ ] **Step 4: Run** → PASS; mypy `Success`.
- [ ] **Step 5: Commit** `feat(core): calendário de mercado`.

### Task 5: Configuração a partir do ambiente

**Files:**
- Create: `backend/src/sinais/core/config.py`, `.env.example`
- Test: `backend/tests/unit/core/test_config.py`

**Interfaces:**
- Produces:
  - `class Ambiente(StrEnum)`: `DESENVOLVIMENTO="dev", TESTE="test", PRODUCAO="prod"`.
  - `class Configuracao(BaseModel, frozen=True)`: `ambiente: Ambiente`, `database_url: SecretStr`, `redis_url: SecretStr`, `nivel_log: Literal["DEBUG","INFO","WARNING","ERROR"] = "INFO"`, `binance_ws_url: str = "wss://data-stream.binance.vision"`, `binance_rest_url: str = "https://api.binance.com"`.
  - `class ErroConfiguracao(Exception)`.
  - `def carregar_configuracao(env: Mapping[str, str] | None = None) -> Configuracao` — lê `SINAIS_AMBIENTE`, `SINAIS_DATABASE_URL`, `SINAIS_REDIS_URL`, `SINAIS_NIVEL_LOG`, `SINAIS_BINANCE_WS_URL`, `SINAIS_BINANCE_REST_URL` (padrão: `os.environ`). Erros de validação viram `ErroConfiguracao` com mensagem que nomeia a variável (`SINAIS_...`) e **nunca** inclui o valor.

- [ ] **Step 1: Write the failing tests:**
  - `test_carrega_valores_validos`: env completo → `cfg.ambiente == Ambiente.DESENVOLVIMENTO`, `cfg.database_url.get_secret_value() == "postgresql://u:p@db/sinais"`
  - `test_padroes`: sem `SINAIS_NIVEL_LOG` → `"INFO"`; WS padrão `wss://data-stream.binance.vision`
  - `test_falta_obrigatoria_nomeia_variavel`: sem `SINAIS_DATABASE_URL` → `ErroConfiguracao` e `"SINAIS_DATABASE_URL" in str(exc)` (Review Focus 4)
  - `test_valor_invalido_nao_vaza_segredo`: `SINAIS_AMBIENTE="xyz"` com `SINAIS_DATABASE_URL="postgresql://u:SEGREDO@db/x"` → mensagem contém `"SINAIS_AMBIENTE"` e não contém `"SEGREDO"`
  - `test_repr_esconde_segredos`: `"p@db" not in repr(cfg)`
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** com pydantic v2 (`model_validate` + tradução de `ValidationError`). `.env.example` com as seis variáveis e valores de desenvolvimento local (`postgresql://sinais:sinais@localhost:5432/sinais`, `redis://localhost:6379/0`).
- [ ] **Step 4: Run** → PASS; mypy `Success`.
- [ ] **Step 5: Commit** `feat(core): configuração por ambiente`.

### Task 6: Logs estruturados em JSON

**Files:**
- Create: `backend/src/sinais/logs.py`
- Test: `backend/tests/unit/test_logs.py`

**Interfaces:**
- Consumes: `Relogio`, `para_iso` (Task 2).
- Produces:
  - `class FormatadorJson(logging.Formatter)` — saída: uma linha JSON com `ts`, `nivel`, `logger`, `evento` (a mensagem) e todo campo passado em `extra={"campos": {...}}`; com exceção, o campo `excecao` traz o traceback como string.
  - `def configurar_logs(nivel: str = "INFO", fluxo: TextIO | None = None) -> None` — configura o logger raiz com `FormatadorJson` num `StreamHandler` (padrão `sys.stdout`), idempotente (chamar duas vezes não duplica handlers).
  - `def obter_logger(nome: str) -> logging.Logger`.

- [ ] **Step 1: Write the failing tests** (capturando com `io.StringIO`):
  - `test_linha_json_com_campos`: `log.info("candle.fechado", extra={"campos": {"ativo": "BTCUSDT"}})` → uma linha; `json.loads` → `evento == "candle.fechado"`, `ativo == "BTCUSDT"`, `nivel == "INFO"`, `ts` termina com `"Z"`
  - `test_excecao_em_campo_unico`: dentro de `except`, `log.exception("falhou")` → saída tem exatamente 1 linha e `"ZeroDivisionError" in obj["excecao"]` (Review Focus 5)
  - `test_idempotente`: `configurar_logs` duas vezes → um evento gera uma linha
  - `test_nivel_filtra`: nível `"WARNING"` → `info` não escreve nada
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** só com a stdlib (`logging`, `json`, `traceback`). `ts` vem de `record.created` convertido para ms e formatado com `para_iso`.
- [ ] **Step 4: Run** → PASS; mypy `Success`.
- [ ] **Step 5: Commit** `feat: logs estruturados em JSON`.

### Task 7: Infraestrutura Docker Compose

**Files:**
- Create: `infra/docker-compose.yml`, `infra/docker/backend.Dockerfile`, `infra/README.md`

**Interfaces:**
- Produces: serviços `db` (imagem `timescale/timescaledb:latest-pg18`, banco/usuário/senha `sinais` vindos de `.env`, volume `dados_db`, healthcheck `pg_isready`), `redis` (`redis:8-alpine`, healthcheck `redis-cli ping`), `backend` (build do Dockerfile, `depends_on` com `condition: service_healthy`, comando `python -c "import sinais"` até existir um processo real).

- [ ] **Step 1: Write** os três arquivos. Dockerfile multi-stage: `python:3.13-slim`, `uv sync --frozen --no-dev`, usuário não root.
- [ ] **Step 2: Run** `docker compose -f infra/docker-compose.yml --env-file .env.example config -q` → sai com código 0.
- [ ] **Step 3: Commit** `chore(infra): docker compose com timescaledb e redis`.

Subir os contêineres (`docker compose up`) exige o daemon do Docker e acesso à rede para baixar imagens. Esse critério é verificado no ambiente do cliente ou no CI.

### Task 8: CI, documentação da fase e progresso

**Files:**
- Create: `.github/workflows/ci.yml`, `docs/fases/fase-02.md`, `docs/adr/` (um arquivo por ADR-01 a ADR-15, resumo da tabela §7.2 do design)
- Modify: `docs/PROGRESSO.md`

- [ ] **Step 1: Write** `ci.yml`: gatilhos `push` e `pull_request`; job `backend` em `ubuntu-latest` com `astral-sh/setup-uv`, `uv sync`, `uv run ruff check`, `uv run ruff format --check`, `uv run mypy`, `uv run pytest --cov=sinais.core --cov-fail-under=90`; job `infra` com `docker compose ... config -q`.
- [ ] **Step 2: Run** localmente `python -m pytest --cov=sinais.core --cov-fail-under=90` (se `pytest-cov` estiver disponível; senão registrar) e `python -m mypy` → passam.
- [ ] **Step 3: Write** `docs/fases/fase-02.md` com objetivo, o que foi entregue, resultado dos testes (saída real), auditoria (o que foi e o que não foi verificado) e critérios de aprovação. Atualizar `PROGRESSO.md`: Fase 1 aprovada em 2026-11-25; Fase 2 em revisão.
- [ ] **Step 4: Commit** `docs: CI, ADRs e registro da Fase 2`.
