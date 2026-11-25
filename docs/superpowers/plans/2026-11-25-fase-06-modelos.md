# Fase 6 — Modelos e Calibração: Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Treinar um classificador por ativo × expiração sobre as features `fs-1`, em walk-forward purgado com calibração em mês separado, decidir COMPRA/VENDA/AGUARDAR por limiar acima do equilíbrio, simular fora da amostra com as regras da Exnova, comparar com as baselines no mesmo período e gerar o **relatório de decisão** (design §13.3, Fase 6), com holdout final intocado.

**Architecture:** `sinais.modelos` com rótulos (`rotulos.py`), treino e calibração (`treino.py`), avaliação walk-forward (`avaliacao.py`), registro em arquivo (`registro.py`) e o relatório de decisão (`decisao.py`, CLI). O workflow "Modelos" roda tudo no GitHub com 24 meses reais e publica o relatório.

**Tech Stack:** scikit-learn 1.9 (`HistGradientBoostingClassifier`, `CalibratedClassifierCV` + `FrozenEstimator`), joblib, pandas, numpy.

**Spec:** design §5 (IA híbrida), §13 (validação), ADR-08/09, §17 Fase 6.

## Global Constraints

- Modelo: `HistGradientBoostingClassifier` (equivalente ao LightGBM, já no ecossistema; ADR-08 ajustado), `max_iter=200`, `learning_rate=0.05`, `max_leaf_nodes=31`, `l2_regularization=1.0`, `early_stopping=False`, `random_state=0`.
- Rótulo: decisão no fechamento de cada minuto; alvo = vencimento da Exnova para a decisão; `1` se o preço no alvo > preço de entrada, `0` se menor; empate fora do treino. Preço por `SeriePrecos` de 1 min (limite superior otimista, declarado).
- Features: todas as colunas de `montar_snapshot` exceto as de idade de contexto (`*_idade_ctx`), em float32. Linhas com rótulo ausente saem.
- Treino com subamostragem de 1 a cada 3 minutos (reduz custo e autocorrelação). Purga pelo fim real do rótulo e embargo de 1 h antes da calibração e antes do teste.
- Calibração isotônica no mês de calibração. Erro de calibração esperado (ECE, 10 faixas) reportado.
- Decisão: COMPRA se `p ≥ limiar`, VENDA se `p ≤ 1 − limiar`, senão AGUARDAR; `limiar = p* + 0,01`.
- Aprovação (design §13.3): ≥ 300 operações decididas fora da amostra, Wilson inferior > `p*` + 1 p.p., acima de todas as baselines no mesmo período, ≥ 70% dos meses civis acima de `p*`, Benjamini-Hochberg sobre todas as combinações, e o holdout (3 meses) também acima de `p*`.
- Nenhum modelo é promovido a campeão sem aprovação.

## Review Focus

1. Rótulo de um minuto cujo vencimento cai depois do fim dos dados: `NaN`, nunca 0. Teste em Task 1.
2. Amostra de treino cujo rótulo termina dentro do embargo da calibração: removida. Teste em Task 3.
3. Modelo que não vê nenhuma amostra de uma classe (mês sem altas): erro claro ou AGUARDAR em tudo, sem exceção opaca. Teste em Task 2.
4. Probabilidade nunca vira sinal fora da faixa `[limiar, 1 − limiar]`: AGUARDAR. Teste em Task 3.
5. Registro: promover um desafiante pior que o campeão é recusado. Teste em Task 4.

---

### Task 1: Rótulos
`modelos/rotulos.py`: `rotular(df_1m, regra, precos) -> pd.DataFrame` com `decisao`, `vencimento_t`, `alvo` (1/0/NaN). Tests: alta/baixa/empate/fim dos dados.

### Task 2: Treino e calibração
`modelos/treino.py`: `colunas_modelo(snapshot) -> list[str]`; `treinar(X, y, X_cal, y_cal) -> ModeloCalibrado` (`probabilidade(X) -> np.ndarray`); `ece(p, y, faixas=10) -> float`; `ErroTreino` quando falta uma classe. Tests: sinal sintético aprendível (feature = rótulo com ruído → AUC > 0,9), calibração melhora ECE, classe única → `ErroTreino`.

### Task 3: Avaliação walk-forward
`modelos/avaliacao.py`: `sinais_do_modelo(decisoes, p, limiar) -> pd.DataFrame`; `avaliar_combinacao(df_1m, snapshot, expiracao, payout, ...) -> ResultadoCombinacao` (operações fora da amostra concatenadas, holdout, baselines no mesmo período, ECE médio, dobras usadas). Tests: limiar (Review Focus 4), purga/embargo (Review Focus 2), execução ponta a ponta num passeio sintético (sem vantagem → não aprovado).

### Task 4: Registro de modelos
`modelos/registro.py`: `Registro(pasta)` com `salvar(versao, modelo, metricas) -> Path`, `campeao(ativo, expiracao)`, `promover(versao)` que recusa se a taxa fora da amostra não superar a do campeão. Tests incluem Review Focus 5.

### Task 5: Relatório de decisão e workflow
`modelos/decisao.py` (CLI: baixa 24 meses, monta snapshot por ativo, avalia as 5 expirações, gera Markdown/JSON com hipóteses e a recomendação por combinação: "ligar", "não ligar"); `.github/workflows/modelos.yml` (manual, timeout 180 min). Rodar, registrar `docs/laboratorio/…-modelos.md`, `docs/fases/fase-06.md`, `PROGRESSO.md`.
