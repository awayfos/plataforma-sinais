# Fase 5 — Backtesting e Validação: Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Simular sinais com as regras reais da Exnova (vencimento no relógio, prazo de compra, empate devolvido, payout), medir resultado com estatística honesta (Wilson, ponto de equilíbrio, Benjamini-Hochberg), comparar com estratégias simples, dividir o tempo em walk-forward purgado e rodar o laboratório no GitHub sobre 2 anos de dados reais da Binance.

**Architecture:** Funções puras em `sinais.corretoras` (regras de vencimento e liquidação) e `sinais.backtest` (preços, simulador, métricas, baselines, walk-forward, relatório). O laboratório (`python -m sinais.backtest.laboratorio`) baixa os arquivos mensais oficiais de `data.binance.vision`, roda as baselines em cada ativo e expiração e grava um relatório Markdown/JSON. Um workflow manual do GitHub Actions executa o laboratório e publica o relatório como artefato.

**Tech Stack:** Python 3.13, pandas, numpy, httpx (download), GitHub Actions `workflow_dispatch`.

**Spec:** design §3 (payout, `p*`), §12 passos 5–8, §13.1–13.3, §16; decisões do cliente sobre o vencimento na Exnova (§12.6).

## Global Constraints

- Vencimento alinhado ao relógio. O vencimento é o primeiro múltiplo da grade com pelo menos `corte` restante. Confirmados: 1 min (grade 60 s, corte 30 s) e 15 min (grade 900 s, corte 300 s). Hipóteses até confirmar na Exnova: 5 min (grade 300 s, corte 100 s), 30 min (1800 s, 600 s), 1 h (3600 s, 1200 s).
- Empate (preço de vencimento = preço de entrada) devolve o valor: resultado 0, fora da taxa de acerto, dentro do valor esperado.
- `p* = 1 / (1 + payout)`. Payout padrão **hipotético** de 0,85 até o cliente informar os valores reais (sempre declarado no relatório).
- Entrada simulada = decisão + latência (padrão 2 s). Sem dado de 1 s, o preço de entrada é a abertura do minuto seguinte à decisão e o de vencimento é o fechamento do minuto que termina no vencimento. Essa aproximação vai declarada no relatório.
- Um sinal ativo por ativo × expiração: sinais durante um sinal ativo são descartados.
- Limite inferior de Wilson com 95% (z = 1,959964).
- Dados de teste sintéticos e rotulados. Relatórios do laboratório só com dados reais e com a fonte declarada.

## Review Focus

1. Compra exatamente no corte (ex.: 00:30:30 em 1 min): vai para o vencimento seguinte, não para o atual. Teste em Task 1.
2. Sinal cuja entrada cai fora da janela de compra (latência alta): não vira operação; conta como "fora_da_janela". Teste em Task 3.
3. Série sem nenhuma operação: métricas devolvem n = 0 e NaN, sem divisão por zero. Teste em Task 4.
4. Walk-forward: nenhuma amostra de treino tem rótulo que termina depois do início do teste (purga) nem dentro do embargo. Teste em Task 5.
5. Mês faltando no download: o laboratório registra a lacuna e segue. Teste em Task 6.

---

### Task 1: Regras de vencimento e liquidação da corretora

**Files:** `backend/src/sinais/corretoras/__init__.py`, `corretoras/regras.py`. Test `tests/unit/corretoras/test_regras.py`.

**Produces:** `@dataclass(frozen=True) RegraVencimento(grade_ms, corte_ms)` com `vencimento_para(compra: InstanteMs) -> InstanteMs` e `prazo_compra(vencimento) -> InstanteMs` (último instante de compra aceito = `vencimento - corte - 1`); `@dataclass(frozen=True) PerfilCorretora(nome, regras: Mapping[Expiracao, RegraVencimento], payout: Mapping[Expiracao, float], hipoteses: frozenset[Expiracao])`; `EXNOVA: PerfilCorretora`; `class Resultado(StrEnum)`: `WIN, LOSS, TIE`; `liquidar(direcao, entrada: float, vencimento: float) -> Resultado`; `ponto_equilibrio(payout) -> float`.

**Tests:** 00:30:10 → 00:31:00; 00:30:29.999 → 00:31:00; **00:30:30.000 → 00:32:00**; 15 min: 00:39:59 → 00:45; 00:40:00 → 01:00; prazo de compra de 00:45 = 00:39:59.999; liquidar compra/venda/empate; `ponto_equilibrio(0.85) ≈ 0.5405`.

### Task 2: Série de preços para liquidação

**Files:** `backtest/__init__.py`, `backtest/precos.py`. Test `tests/unit/backtest/test_precos.py`.

**Produces:** `class SeriePrecos` construída de um quadro de 1 s **ou** de 1 m (`de_quadro(df, intervalo_ms)`), com `preco_em(t: InstanteMs) -> float | None`: com 1 s, o fechamento do candle de 1 s que termina em `t` (ou o mais recente até `t`); com 1 m, só em fronteiras de minuto (abertura do minuto que começa em `t` se existir, senão fechamento do que termina em `t`), `None` fora delas; `granularidade_ms`.

**Tests:** 1 s exato; 1 m na fronteira; 1 m dentro do minuto → `None`; lacuna → `None`.

### Task 3: Simulador de operações

**Files:** `backtest/simulador.py`. Test `test_simulador.py`.

**Produces:** `simular(sinais: pd.DataFrame, precos: SeriePrecos, regra: RegraVencimento, latencia_ms: int = 2000) -> pd.DataFrame` — `sinais` com colunas `decisao` (ms), `direcao` (+1/−1). Saída por sinal: `entrada_t`, `vencimento_t`, `preco_entrada`, `preco_vencimento`, `resultado` (`WIN/LOSS/TIE/FORA_DA_JANELA/SEM_DADO/IGNORADO_ATIVO`), `margem` (vencimento − entrada, com sinal da direção). Com granularidade de 1 m, a entrada arredonda para a próxima fronteira de minuto ≥ decisão + latência.

**Tests:** compra que ganha; venda que perde; empate; entrada depois do prazo de compra → `FORA_DA_JANELA` (Review Focus 2); sinal durante sinal ativo → `IGNORADO_ATIVO`; preço ausente → `SEM_DADO`.

### Task 4: Métricas, Wilson e Benjamini-Hochberg

**Files:** `backtest/metricas.py`. Test `test_metricas.py`.

**Produces:** `wilson(acertos, n, z=1.959964) -> tuple[float, float]`; `@dataclass Metricas(n, wins, losses, ties, fora_janela, sem_dado, taxa, wilson_inf, wilson_sup, p_equilibrio, valor_esperado)`; `calcular(operacoes, payout) -> Metricas`; `por_grupo(operacoes, payout, chave: Callable[[pd.DataFrame], pd.Series]) -> dict[str, Metricas]` (ex.: hora UTC); `benjamini_hochberg(pvalores: Sequence[float], q=0.05) -> list[bool]`; `pvalor_acima_equilibrio(acertos, n, p_eq) -> float` (binomial unilateral exato).

**Tests:** Wilson conhecido (8/10 → [0,4902; 0,9433]); n = 0 → NaN sem erro (Review Focus 3); valor esperado com empates; BH no exemplo clássico; p-valor binomial exato em caso pequeno.

### Task 5: Baselines e walk-forward purgado

**Files:** `backtest/baselines.py`, `backtest/walk_forward.py`. Tests.

**Produces:** baselines que recebem o quadro de 1 m e devolvem `sinais` (uma decisão por minuto fechado): `sempre_compra`, `sempre_venda`, `seguir_ultimo` (direção do último candle; doji não sinaliza), `aleatoria(semente, prob=1.0)`. `@dataclass Dobra(treino: tuple[int,int], calibracao: tuple[int,int], teste: tuple[int,int])`; `dobras(inicio, fim, treino_meses=6, calibracao_meses=1, teste_meses=1, embargo_ms) -> list[Dobra]`; `purgar(decisoes: pd.Series, horizonte_ms: int, ate: InstanteMs, embargo_ms) -> pd.Series[bool]` (mantém só amostras cujo rótulo termina antes de `ate - embargo`).

**Tests:** sinais das baselines; dobras contíguas e sem sobreposição; purga remove amostra cujo rótulo cruza o teste (Review Focus 4).

### Task 6: Laboratório com dados reais e workflow

**Files:** `backtest/historico.py` (URLs e leitura dos zips mensais `https://data.binance.vision/data/spot/monthly/klines/{SIMB}/{int}/{SIMB}-{int}-{AAAA}-{MM}.zip`, CSV sem cabeçalho, 12 colunas, tempo em ms ou µs), `backtest/relatorio.py`, `backtest/laboratorio.py`, `.github/workflows/laboratorio.yml` (`workflow_dispatch` com entradas `meses` e `payout`; artefato `relatorio-laboratorio`). Tests: leitura de CSV em ms e em µs; mês 404 vira lacuna registrada (Review Focus 5); relatório com cabeçalho de hipóteses (payout, aproximação de preço, fonte).

**Then:** disparar o workflow, ler o relatório, registrar em `docs/fases/fase-05.md`, `PROGRESSO.md`, revisão final.
