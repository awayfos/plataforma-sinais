# Fase 3 — Dados de Mercado da Binance: Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Coletar candles fechados de 1 s e 1 min de BTCUSDT e ETHUSDT da Binance Spot (histórico por REST e tempo real por WebSocket), validar a qualidade, agregar tempos gráficos maiores, gravar no PostgreSQL/TimescaleDB e publicar `candle.fechado` no Redis Streams.

**Architecture:** Portas e adaptadores. A lógica (modelos, parsing, qualidade, agregação, janelas de backfill, laço de consumo com reconexão, serviço de backfill, processo coletor) é Python puro e testada localmente com dublês. Os adaptadores de I/O (httpx, websockets, SQLAlchemy/asyncpg, redis) são finos e testados no CI do GitHub, que tem rede e serviços em contêiner.

**Tech Stack:** Python 3.13, `decimal.Decimal` para preços, httpx, websockets, SQLAlchemy 2 (Core, async) + asyncpg + Alembic, redis-py (asyncio), pytest-asyncio (só CI), GitHub Actions com serviços `timescale/timescaledb:latest-pg18` e `redis:8-alpine`.

**Spec:** `docs/superpowers/specs/2026-11-25-plataforma-sinais-design.md` (§3 restrições da Binance, §9 `dados.*`, §10 eventos, §11 tabelas de mercado, §12 passos 1–3, §17 Fase 3)

## Global Constraints

- Só candles **fechados** são gravados e publicados (na Binance, `k.x == true`; no REST, só linhas com `close time < agora`).
- Preços e volumes como `Decimal` construído a partir da string da Binance. Nunca `float` na coleta.
- Instantes em `InstanteMs` (Fase 2). Abertura do candle alinhada ao intervalo.
- REST `GET /api/v3/klines`: peso 2, `limit` máximo 1000, resposta com 12 campos na ordem: open time, open, high, low, close, volume, close time, quote volume, trades, taker buy base, taker buy quote, ignore.
- WebSocket: base `wss://data-stream.binance.vision` (só dados de mercado), streams combinados `/stream?streams=a/b`, máximo 1024 streams por conexão, conexão derrubada em 24 h (renovar antes, aos 23 h 50 min), 5 mensagens recebidas por segundo, 300 conexões a cada 5 min por IP.
- Intervalos coletados: `1s` e `1m`. Tempos gráficos maiores derivam de `1m` localmente.
- Erros HTTP 429 e 418 respeitam `Retry-After`. 5xx e falhas de rede: até 5 tentativas com backoff exponencial e jitter (base 1 s, teto 60 s).
- Inserções idempotentes: PK `(simbolo, abertura)` por tabela, `ON CONFLICT DO NOTHING`.
- Histórico inicial configurável por `SINAIS_HISTORICO_DIAS` (padrão 730).
- Testes que precisam de pacote ausente localmente usam `pytest.importorskip` e a marca `integracao`. O CI roda todos.

## Review Focus

1. Mensagem do WebSocket com `x=false` (candle em formação) nunca é gravada nem publicada como fechada. Teste em Task 1 e Task 7.
2. Reconexão no meio do histórico: o intervalo entre o último candle gravado e o primeiro recebido ao vivo é preenchido por REST antes de publicar candles novos. Teste em Task 7.
3. Minuto faltando dentro de um bloco de 5 min: o candle de 5 min **não** é emitido, e a lacuna vira evento de qualidade. Teste em Task 2.
4. Resposta REST com linha malformada (campos faltando, preço não numérico, high < low): erro explícito com o símbolo e a abertura, sem gravar a página parcial. Teste em Task 1 e Task 3.
5. 429 com `Retry-After: 7`: o cliente espera 7 s (relógio injetável) e tenta de novo, sem estourar o limite. Teste em Task 3.

---

### Task 1: Modelo de candle e parsing da Binance

**Files:** Create `backend/src/sinais/dados/__init__.py`, `backend/src/sinais/dados/modelos.py`, `backend/src/sinais/dados/provedores/__init__.py`, `backend/src/sinais/dados/provedores/binance/__init__.py`, `backend/src/sinais/dados/provedores/binance/parsing.py`. Test `backend/tests/unit/dados/test_modelos.py`, `backend/tests/unit/dados/test_parsing_binance.py`.

**Interfaces — Produces:**
- `class IntervaloColeta(StrEnum)`: `S1="1s"`, `M1="1m"`; propriedade `duracao_ms`.
- `@dataclass(frozen=True, slots=True) class Candle`: `simbolo: str`, `intervalo_ms: int`, `abertura: InstanteMs`, `abertura_preco: Decimal`, `maxima: Decimal`, `minima: Decimal`, `fechamento: Decimal`, `volume: Decimal`, `volume_cotacao: Decimal`, `negocios: int`, `volume_compra_agressora: Decimal`, `fonte: str`. Propriedade `fechamento_ms = abertura + intervalo_ms`. `__post_init__` → `ValueError` se abertura não alinhada, `maxima < max(abertura_preco, fechamento)`, `minima > min(...)`, volume ou negócios negativos.
- `class ErroParsing(ValueError)`, mensagem com símbolo e abertura quando disponíveis.
- `def de_linha_rest(simbolo: str, intervalo: IntervaloColeta, linha: Sequence[object]) -> Candle`
- `@dataclass(frozen=True) class EventoKline`: `candle: Candle`, `fechado: bool`, `evento_ms: InstanteMs`.
- `def de_mensagem_ws(texto: str) -> EventoKline | None` — aceita o envelope combinado `{"stream","data"}` e o evento cru; devolve `None` para eventos que não são `kline`.

**Tests:** `test_candle_valido`, `test_candle_maxima_menor_que_fechamento_rejeita`, `test_candle_abertura_desalinhada_rejeita`, `test_linha_rest_ok` (linha real da documentação, ex. `[1499040000000,"0.01634790","0.80000000","0.01575800","0.01577100","148976.11427815",1499644799999,"2434.19055334",308,"1756.87402397","28.46694368","0"]` com intervalo 1m ajustado para abertura alinhada), `test_linha_rest_curta_rejeita`, `test_linha_rest_preco_invalido_rejeita` (mensagem contém o símbolo), `test_ws_envelope_combinado_fechado`, `test_ws_em_formacao_fechado_false` (Review Focus 1), `test_ws_evento_nao_kline_devolve_none`, `test_ws_json_invalido_rejeita`.

- [ ] Write the failing tests → run `python -m pytest tests/unit/dados -q` → FAIL
- [ ] Implement → PASS; `python -m mypy` → Success
- [ ] Commit `feat(dados): modelo de candle e parsing da Binance`

### Task 2: Qualidade, agregação e janelas de backfill

**Files:** Create `backend/src/sinais/dados/qualidade.py`, `backend/src/sinais/dados/agregacao.py`, `backend/src/sinais/dados/backfill.py` (só a função pura nesta task). Test `backend/tests/unit/dados/test_qualidade.py`, `test_agregacao.py`, `test_janelas.py`.

**Interfaces — Produces:**
- `@dataclass(frozen=True) class Lacuna`: `inicio: InstanteMs`, `fim: InstanteMs` (fim exclusivo).
- `@dataclass(frozen=True) class RelatorioQualidade`: `lacunas: tuple[Lacuna, ...]`, `duplicados: tuple[InstanteMs, ...]`, `fora_de_ordem: tuple[InstanteMs, ...]`; propriedade `ok: bool`.
- `def verificar_sequencia(candles: Sequence[Candle], intervalo_ms: int) -> RelatorioQualidade`
- `def agregar(candles_1m: Sequence[Candle], tg: TempoGrafico) -> list[Candle]` — emite só blocos completos e contíguos; abertura = abertura do 1º, fechamento = do último, máxima/mínima extremas, volumes e negócios somados; `fonte="agregado"`.
- `class AgregadorIncremental(tg: TempoGrafico)`: `def adicionar(self, c: Candle) -> Candle | None` — devolve o candle do tempo gráfico maior quando o último minuto do bloco chega e o bloco está completo; um bloco com minuto faltando é descartado.
- `def janelas_backfill(inicio: InstanteMs, fim: InstanteMs, intervalo_ms: int, limite: int = 1000) -> list[tuple[InstanteMs, InstanteMs]]` — janelas `[a, b)` cobrindo `[inicio, fim)`, cada uma com no máximo `limite` candles.

**Tests:** `test_sequencia_ok`, `test_detecta_lacuna`, `test_detecta_duplicado`, `test_detecta_fora_de_ordem`, `test_agrega_5m_completo` (5 candles 1m → 1 candle com valores conferidos à mão), `test_bloco_incompleto_nao_emite` (Review Focus 3), `test_agrega_semana_alinhada_segunda`, `test_incremental_emite_no_ultimo_minuto`, `test_incremental_descarta_bloco_com_lacuna`, `test_janelas_exatas` (2.500 minutos → 3 janelas: 1000, 1000, 500), `test_janelas_vazio_quando_inicio_igual_fim`.

- [ ] Failing tests → FAIL → implement → PASS; mypy Success
- [ ] Commit `feat(dados): qualidade, agregação e janelas de backfill`

### Task 3: Dependências de I/O e cliente REST da Binance

**Files:** Modify `backend/pyproject.toml` (deps `httpx>=0.28`, `websockets>=15`, `sqlalchemy[asyncio]>=2.0.40`, `asyncpg>=0.30`, `alembic>=1.15`, `redis>=6`; dev `pytest-asyncio>=1`; marca `integracao`; mypy `ignore_missing_imports` só para `asyncpg`). Create `backend/src/sinais/dados/provedores/binance/rest.py`. Test `backend/tests/integracao/test_rest_binance.py` (httpx `MockTransport`, sem rede real).

**Interfaces — Produces:**
- `class ErroLimiteTaxa(Exception)`: atributo `espera_s: float`.
- `class ClienteRestBinance(base_url: str, http: httpx.AsyncClient, dormir: Callable[[float], Awaitable[None]] = asyncio.sleep, tentativas: int = 5)`:
  - `async def hora_servidor(self) -> InstanteMs` (`GET /api/v3/time`)
  - `async def klines(self, simbolo: str, intervalo: IntervaloColeta, inicio: InstanteMs, fim: InstanteMs, limite: int = 1000) -> list[Candle]` (`endTime = fim - 1`; descarta linhas cujo `close time >= agora do servidor` não é responsabilidade daqui: o chamador passa `fim` ≤ agora alinhado)
- `def atraso_backoff(tentativa: int, base_s: float = 1.0, teto_s: float = 60.0, aleatorio: Callable[[], float] = random.random) -> float` (em `sinais/dados/provedores/backoff.py`, puro, teste local).

**Tests:** local `test_backoff.py`: `test_backoff_cresce_e_respeita_teto`, `test_backoff_com_jitter_entre_metade_e_total`. CI: `test_klines_parseia_pagina`, `test_klines_parametros` (symbol, interval, startTime, endTime, limit), `test_429_respeita_retry_after` (Review Focus 5: `dormir` recebe `7.0`), `test_418_levanta_erro_limite`, `test_5xx_tenta_de_novo_e_desiste_apos_5`, `test_linha_malformada_falha_pagina_inteira` (Review Focus 4).

- [ ] Failing tests → run local + CI → FAIL → implement → PASS
- [ ] Commit `feat(dados): cliente REST da Binance`

### Task 4: Consumo de streams com reconexão e renovação

**Files:** Create `backend/src/sinais/dados/provedores/binance/streams.py`. Test local `backend/tests/unit/dados/test_streams.py`; CI `backend/tests/integracao/test_ws_adaptador.py` (servidor `websockets` local).

**Interfaces — Produces:**
- `def nomes_streams(simbolos: Sequence[str], intervalos: Sequence[IntervaloColeta]) -> list[str]` — `btcusdt@kline_1m`; `ValueError` acima de 1024.
- `def url_combinada(base: str, streams: Sequence[str]) -> str` → `"{base}/stream?streams=a/b"`.
- `type Conector = Callable[[str], AbstractAsyncContextManager[AsyncIterator[str]]]`
- `class ConsumidorStreams(url: str, conectar: Conector, relogio: Relogio, ao_mensagem: Callable[[str], Awaitable[None]], ao_reconectar: Callable[[], Awaitable[None]], dormir=asyncio.sleep, renovar_apos_ms: int = 85_800_000)`:
  - `async def executar(self, parar: asyncio.Event) -> None` — conecta, repassa mensagens, renova a conexão aos 23 h 50 min, reconecta com `atraso_backoff` após erro, chama `ao_reconectar` **antes** de repassar mensagens de uma nova conexão (exceto a primeira), zera a contagem de tentativas após receber uma mensagem.
- `def conector_websockets(url: str) -> AbstractAsyncContextManager[AsyncIterator[str]]` — adaptador `websockets.connect` com `ping_interval=None` (o servidor envia ping; a biblioteca responde pong).

**Tests (locais, com conector falso):** `test_nomes_streams`, `test_limite_1024`, `test_url_combinada`, `test_repassa_mensagens`, `test_reconecta_apos_erro_com_backoff`, `test_chama_ao_reconectar_antes_das_novas_mensagens`, `test_renova_conexao_antes_de_24h`, `test_para_quando_evento_parar`. CI: `test_adaptador_recebe_do_servidor_local`.

- [ ] Failing tests → FAIL → implement → PASS
- [ ] Commit `feat(dados): consumo de streams com reconexão`

### Task 5: Persistência de candles e migrações

**Files:** Create `backend/src/sinais/persistencia/__init__.py`, `tabelas.py`, `repositorio_candles.py`, `backend/alembic.ini`, `backend/migracoes/env.py`, `backend/migracoes/versions/0001_mercado.py`. Test CI `backend/tests/integracao/test_repositorio_candles.py`.

**Interfaces — Produces:**
- Tabelas `candles_1m`, `candles_1s` (colunas do `Candle`; preços `NUMERIC(28,12)`; `abertura TIMESTAMPTZ`; PK `(simbolo, abertura)`; `ingerido_em TIMESTAMPTZ DEFAULT now()`), `eventos_qualidade` (id bigserial, simbolo, intervalo, inicio, fim, tipo, detalhes JSONB, criado_em). Migração cria a extensão `timescaledb` e transforma as duas tabelas de candles em hypertables (`create_hypertable(..., 'abertura', if_not_exists => TRUE)`).
- `class RepositorioCandles(Protocol)`: `async def inserir(self, candles: Sequence[Candle]) -> int`; `async def ultima_abertura(self, simbolo: str, intervalo: IntervaloColeta) -> InstanteMs | None`; `async def listar(self, simbolo, intervalo, inicio, fim) -> list[Candle]`; `async def registrar_qualidade(self, simbolo: str, intervalo: IntervaloColeta, lacuna: Lacuna, tipo: str) -> None`.
- `class RepositorioCandlesPg(engine: AsyncEngine)` implementando o protocolo. `inserir` devolve quantas linhas entraram (duplicadas não contam).
- Em `sinais/dados/memoria.py`: `RepositorioCandlesMemoria` (dublê para testes locais, mesmo protocolo).

**Tests (CI, com o serviço timescale):** `test_migracao_cria_hypertables`, `test_inserir_e_listar_ida_e_volta` (Decimal idêntico), `test_inserir_idempotente`, `test_ultima_abertura`, `test_registrar_qualidade`. Local: `test_repositorio_memoria_mesmo_contrato` (os mesmos casos contra o dublê).

- [ ] Failing tests → FAIL → implement → PASS
- [ ] Commit `feat(persistencia): candles no TimescaleDB e migrações`

### Task 6: Publicação de eventos no Redis Streams

**Files:** Create `backend/src/sinais/eventos/__init__.py`, `contratos.py`, `redis_streams.py`, `memoria.py`. Test local `backend/tests/unit/eventos/test_contratos.py`; CI `backend/tests/integracao/test_redis_streams.py`.

**Interfaces — Produces:**
- `def evento_candle_fechado(c: Candle) -> dict[str, str]` — campos `versao="1"`, `id="{simbolo}:{intervalo_ms}:{abertura}"`, `simbolo`, `intervalo_ms`, `abertura`, `o,h,l,c,v` como string, `fonte`.
- `STREAM_CANDLE_FECHADO = "candle.fechado"`.
- `class Publicador(Protocol)`: `async def publicar(self, stream: str, campos: Mapping[str, str]) -> None`.
- `class PublicadorRedis(redis: Redis, maxlen: int = 100_000)` (XADD com `approximate=True`); `class PublicadorMemoria` (dublê).

**Tests:** `test_evento_campos_e_id`, `test_decimal_preservado_como_string`; CI `test_xadd_e_leitura_por_grupo`.

- [ ] Failing tests → FAIL → implement → PASS
- [ ] Commit `feat(eventos): candle.fechado no Redis Streams`

### Task 7: Serviço de backfill e processo coletor

**Files:** Modify `backend/src/sinais/dados/backfill.py`; create `backend/src/sinais/processos/__init__.py`, `backend/src/sinais/processos/coletor_binance.py`; modify `backend/src/sinais/core/config.py` (campo `historico_dias: int = 730`, var `SINAIS_HISTORICO_DIAS`). Test local `backend/tests/unit/processos/test_coletor.py`, `backend/tests/unit/dados/test_backfill_servico.py`.

**Interfaces — Produces:**
- `class FonteHistorico(Protocol)`: `async def klines(...)` com a assinatura do `ClienteRestBinance.klines`.
- `async def preencher(fonte: FonteHistorico, repo: RepositorioCandles, simbolo: str, intervalo: IntervaloColeta, inicio: InstanteMs, fim: InstanteMs) -> int` — usa `janelas_backfill`, grava página a página, verifica a sequência gravada e registra lacunas restantes como `tipo="lacuna_rest"`.
- `class Coletor(simbolos, intervalos, fonte, repo, publicador, relogio, historico_dias)`:
  - `async def sincronizar(self) -> None` — para cada símbolo e intervalo, preenche de `max(ultima_abertura + intervalo, agora - historico_dias)` até a abertura do candle atual (exclusivo).
  - `async def ao_mensagem(self, texto: str) -> None` — parse; ignora `fechado=False`; grava; se gravou (não duplicado), publica `candle.fechado`; para `1m`, alimenta `AgregadorIncremental` e publica os tempos gráficos maiores emitidos.
  - `async def ao_reconectar(self) -> None` — chama `sincronizar()`.
- `async def principal() -> None` e `if __name__ == "__main__"`: configura logs, carrega config, cria httpx/engine/redis, roda `sincronizar()` e depois `ConsumidorStreams.executar`.

**Tests (locais, com dublês):** `test_preencher_grava_todas_as_janelas`, `test_preencher_registra_lacuna_restante`, `test_sincronizar_inicial_usa_historico_dias`, `test_sincronizar_continua_do_ultimo`, `test_mensagem_em_formacao_ignorada` (Review Focus 1), `test_mensagem_fechada_grava_e_publica`, `test_duplicada_nao_publica_de_novo`, `test_reconectar_preenche_lacuna_antes_de_publicar` (Review Focus 2), `test_publica_5m_quando_bloco_completa`.

- [ ] Failing tests → FAIL → implement → PASS
- [ ] Commit `feat(processos): coletor da Binance`

### Task 8: Infraestrutura, CI e documentação

**Files:** Modify `infra/docker-compose.yml` (serviço `migracoes` com `alembic upgrade head`; `backend` → `python -m sinais.processos.coletor_binance`, `restart: unless-stopped`, depende de `migracoes` concluído com sucesso), `.github/workflows/ci.yml` (job `integracao` com serviços timescale e redis, `pytest -m integracao`), `.env.example` (`SINAIS_HISTORICO_DIAS`). Create `docs/fases/fase-03.md`. Modify `docs/PROGRESSO.md`.

- [ ] Push branch → CI verde nos jobs `backend`, `integracao`, `infra`
- [ ] Registrar resultados reais e auditoria em `docs/fases/fase-03.md`; atualizar `PROGRESSO.md`
- [ ] Commit `docs: registro da Fase 3`
