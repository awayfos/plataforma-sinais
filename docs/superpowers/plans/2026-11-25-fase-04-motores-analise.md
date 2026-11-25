# Fase 4 — Motores de Análise: Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Biblioteca única e causal de análise técnica (indicadores, padrões de candle, estrutura, regiões, volume, price action, Fibonacci) e o snapshot de features multi-tempo-gráfico, com teste automático de que nenhum valor em `t` usa dado posterior a `t`.

**Architecture:** Funções puras sobre `pandas.DataFrame` com colunas `o,h,l,c,v,vb` (float64; `vb` = volume comprador agressor) e índice `abertura` (ms). Cada família fica num módulo próprio e só calcula; nada decide operação. `sinais.features` monta o snapshot versionado a partir de um registro de funções, usado igual no laboratório e ao vivo.

**Tech Stack:** Python 3.13, pandas 3, numpy 2 (já instalados localmente).

**Spec:** `docs/superpowers/specs/2026-11-25-plataforma-sinais-design.md` (§9 `analise.*` e `features`, §13.1, §14 "Regressão de vazamento", requisitos 4 e 5 do documento original)

## Global Constraints

- Causalidade: o valor de qualquer saída na linha `t` depende só das linhas `≤ t`. Pivôs (que precisam de candles à direita) só aparecem na linha em que ficam **confirmados**.
- Valores ainda não definidos (aquecimento) são `NaN`, nunca zero.
- Análise em `float64`. A conversão de `Decimal` acontece uma vez, em `para_quadro(candles)`.
- Todos os parâmetros são configuráveis, com os padrões: RSI 14, MACD 12/26/9, Bollinger 20/2 (desvio populacional), ATR 14, ADX 14, Estocástico 14/3/3, Ichimoku 9/26/52, volume relativo 20, pivôs k=3.
- Médias de Wilder (RSI, ATR, ADX): RMA com `alpha = 1/n`, semeada pela média simples dos primeiros `n` valores. EMA: `alpha = 2/(n+1)`, semeada pela SMA dos primeiros `n`.
- Chikou do Ichimoku não entra nas features (usa o futuro). Ele existe só para o gráfico.
- Versão do conjunto de features: `FEATURE_SET_VERSION = "fs-1"`.

## Review Focus

1. Série com volume zero (minutos sem negócio): volume relativo, VWAP e pressão compradora devolvem `NaN` ou valor neutro, sem divisão por zero nem `inf`. Teste em Task 4.
2. Série constante (preço parado): RSI, Estocástico e ADX não geram `inf`/`NaN` espúrio após o aquecimento. RSI = 50, Estocástico = 50. Teste em Task 1.
3. Contexto multi-tempo: em 10:07, a feature de 1h usa o candle 09:00–10:00, nunca o 10:00–11:00 em formação. Teste em Task 6.
4. Pivô no último candle: não pode aparecer antes de `k` candles confirmarem. Teste em Task 3.
5. Quadro com menos linhas que o aquecimento: tudo `NaN`, sem exceção. Teste em Task 6.

---

### Task 1: Quadro de dados e indicadores de tendência e oscilação

**Files:** Create `backend/src/sinais/analise/__init__.py`, `analise/quadro.py`, `analise/indicadores.py`. Test `backend/tests/unit/analise/test_indicadores.py`, `tests/unit/analise/sinteticos.py` (passeio aleatório com semente fixa, rotulado sintético).

**Interfaces — Produces:**
- `def para_quadro(candles: Sequence[Candle]) -> pd.DataFrame` (colunas `o,h,l,c,v,vb`, índice `abertura`).
- `sma(s, n=20)`, `ema(s, n=20)`, `rma(s, n=14)` → `pd.Series`
- `rsi(c, n=14)` → Series; `macd(c, rapida=12, lenta=26, sinal=9)` → DataFrame `macd,sinal,hist`; `bollinger(c, n=20, k=2.0)` → `media,sup,inf,largura`; `atr(df, n=14)`; `adx(df, n=14)` → `adx,mais_di,menos_di`; `estocastico(df, n=14, suav_k=3, d=3)` → `k,d`; `ichimoku(df, 9, 26, 52)` → `tenkan,kijun,span_a,span_b` (spans deslocadas 26 para frente, causais); `chikou(df, 26)` (só gráfico).

**Tests:** SMA/EMA contra valores calculados à mão em série de 6 pontos; `test_rsi_serie_crescente_100`, `test_rsi_constante_50` (Review Focus 2), `test_rsi_wilder_caso_conhecido` (14 variações fixas, valor calculado à mão com a fórmula); `test_macd_hist_igual_macd_menos_sinal`; `test_bollinger_populacional`; `test_atr_true_range_com_gap`; `test_adx_tendencia_forte_maior_que_lateral` (sintético); `test_estocastico_limites_0_100` e constante = 50; `test_ichimoku_spans_deslocadas`; `test_aquecimento_nan`.

### Task 2: Padrões de candle e força

**Files:** Create `analise/padroes_candle.py`. Test `tests/unit/analise/test_padroes_candle.py`.

**Interfaces — Produces:** cada função recebe `df` e devolve `pd.Series` de `int8` (1 alta, −1 baixa, 0 nada) ou `bool`: `doji(df, corpo_max=0.1)`, `martelo(df)`, `estrela_cadente(df)`, `pin_bar(df, pavio_min=2/3)`, `engolfo(df)`, `marubozu(df, pavio_max=0.05)`, `inside_bar(df)`, `outside_bar(df)`, `estrela_manha(df)`, `estrela_tarde(df)`, `sequencia(df)` (candles seguidos na mesma direção, com sinal), `forca(df)` → DataFrame `corpo_rel` (corpo/amplitude), `pressao_compradora` (`vb/v − 0.5`).

**Tests:** um candle construído à mão para cada padrão (positivo) e um contraexemplo cada; `test_amplitude_zero_nao_quebra`.

### Task 3: Pivôs e estrutura de mercado

**Files:** Create `analise/estrutura.py`. Test `tests/unit/analise/test_estrutura.py`.

**Interfaces — Produces:**
- `pivos(df, k=3) -> pd.DataFrame` com colunas `topo` e `fundo` (preço do pivô, `NaN` se não houver) **na linha de confirmação** (`t + k`) e `idade` (k).
- `estrutura(df, k=3) -> pd.DataFrame`: `ultimo_topo`, `ultimo_fundo`, `rotulo_topo` (+1 HH / −1 LH), `rotulo_fundo` (+1 HL / −1 LL), `tendencia` (+1 alta = HH e HL, −1 baixa = LH e LL, 0 indefinida), `bos` (+1/−1 quando o fechamento rompe o último topo/fundo a favor da tendência), `choch` (+1/−1 quando rompe contra a tendência).

**Tests:** zigue-zague construído à mão com topos e fundos conhecidos; `test_pivo_so_confirma_apos_k` (Review Focus 4); `test_hh_hl_tendencia_alta`; `test_bos_alta`; `test_choch_virada`.

### Task 4: Volume e regiões de preço

**Files:** Create `analise/volume.py`, `analise/regioes.py`, `analise/fibonacci.py`. Tests `test_volume.py`, `test_regioes.py`, `test_fibonacci.py`.

**Interfaces — Produces:**
- `volume_relativo(df, n=20)`, `expansao_volume(df, n=20)` (tendência da média curta/longa), `pressao_acumulada(df, n=20)` (soma de `vb − (v − vb)` / soma de `v`), `divergencia_volume(df, n=14)` (preço sobe e volume cai: −1; o inverso: +1). Volume zero → `NaN`.
- `vwap(df, periodo_ms=86_400_000)` reiniciado na virada do dia UTC.
- `regioes(df, k=3, tolerancia_atr=0.5, n_atr=14) -> pd.DataFrame`: `res_dist` e `sup_dist` (distância ao nível mais próximo, em ATR), `res_toques`, `sup_toques` (pivôs agrupados no nível), `rompimento` (+1/−1 fechamento além do nível), `falso_rompimento` (+1/−1 pavio além do nível e fechamento de volta). Só pivôs confirmados entram.
- `niveis_fibonacci(topo: float, fundo: float) -> dict[str, float]` (0, 23,6, 38,2, 50, 61,8, 78,6, 100%) e `posicao_fibonacci(df, k=3)` (posição do fechamento entre o último fundo e o último topo confirmados, de 0 a 1).

**Tests:** volume relativo calculado à mão; `test_volume_zero_nan` (Review Focus 1); VWAP reinicia no dia; regiões com toques conhecidos; falso rompimento construído à mão; níveis de Fibonacci exatos.

### Task 5: Price action

**Files:** Create `analise/price_action.py`. Test `test_price_action.py`.

**Interfaces — Produces:** `price_action(df, n=14) -> pd.DataFrame` com `inclinacao_ema` (EMA 20 em ATR por candle), `impulso` (|c − c[n]| / ATR), `desaceleracao` (impulso atual − impulso de `n/2` candles atrás, negativo = desacelerando), `lateral` (ADX < 20 e largura de Bollinger abaixo da mediana de 100 candles), `rejeicao` (pavio superior − inferior sobre a amplitude), `correcao` (recuo desde o último topo/fundo em ATR, a favor da tendência estrutural), `continuidade` (fração dos últimos `n` candles na direção da EMA).

**Tests:** sintético em tendência → `inclinacao_ema > 0` e `continuidade > 0,5`; série que acelera e depois freia → `desaceleracao < 0` no trecho final; `lateral` verdadeiro em série oscilante.

### Task 6: Snapshot de features multi-tempo e regressão de vazamento

**Files:** Create `backend/src/sinais/features/__init__.py`, `features/snapshot.py`. Test `tests/unit/features/test_snapshot.py`, `tests/regressao_vazamento/test_causalidade.py`.

**Interfaces — Produces:**
- `FEATURE_SET_VERSION = "fs-1"`.
- `def features_de(df: pd.DataFrame) -> pd.DataFrame` — junta todas as famílias com prefixos (`ind_`, `pad_`, `est_`, `vol_`, `reg_`, `fib_`, `pa_`).
- `def montar_snapshot(df_1m: pd.DataFrame, contextos: Sequence[TempoGrafico] = (M5, M15, H1)) -> pd.DataFrame` — features de 1m mais as de cada contexto agregado a partir de 1m, alinhadas pela **hora de fechamento** do candle do contexto (`merge_asof` com `fechamento ≤ fechamento do 1m`), prefixo `m5_`, `m15_`, `h1_`.

**Tests:** `test_colunas_com_prefixo_e_versao`; `test_contexto_usa_candle_fechado` (Review Focus 3); `test_quadro_curto_tudo_nan` (Review Focus 5); **regressão de vazamento**: para 20 instantes sorteados (semente fixa) num passeio aleatório de 3.000 minutos, a linha `t` de `montar_snapshot(df)` é idêntica (NaN = NaN) à última linha de `montar_snapshot(df[:t])`, coluna por coluna; e a mesma linha não muda quando os dados depois de `t` são embaralhados.

Cada task: testes falhando → implementação → `pytest` e `mypy` verdes → `ruff` → commit. Ao final: `docs/fases/fase-04.md`, `PROGRESSO.md`, CI verde, revisão final.
