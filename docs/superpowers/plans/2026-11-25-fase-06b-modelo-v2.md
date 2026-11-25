# Fase 6b — Modelo v2 (rótulos de 1 s, microestrutura, filtro de apertados) — Plano de implementação

> **Para agentes:** SUB-SKILL OBRIGATÓRIA: superpowers:executing-plans (com superpowers:test-driven-development e superpowers:verification-before-completion). Passos com caixas (`- [ ]`).

**Objetivo:** treinar e validar, no padrão da Fase 6, um modelo v2 para BTCUSDT e ETHUSDT em 1m e 5m com rótulos de preços de 1 s, features de microestrutura (`fs-2`) e um filtro que mostra AGUARDAR quando a operação tende a terminar apertada.

**Arquitetura:** os klines de 1 s são baixados mês a mês, agregados por minuto (`features/microestrutura.py`) e descartados; só ficam os fechamentos de 1 s (para rótulos e simulação) e a tabela por minuto. `fs-2` = `fs-1` + microestrutura + calendário. A avaliação v2 (`modelos/avaliacao_v2.py`) repete o walk-forward da Fase 6, mas rotula com entrada sorteada em 1 s e acrescenta um modelo de "apertado" com limiar escolhido só na calibração. O relatório (`modelos/decisao_v2.py`) reaproveita `consolidar` da Fase 6.

**Pilha:** Python 3.13, pandas, numpy, scikit-learn (HistGradientBoosting + isotônica), GitHub Actions.

**Spec:** pedido do coordenador (Trilha A) + design §12–§13 (`docs/superpowers/specs/2026-11-25-plataforma-sinais-design.md`) + `docs/fases/fase-06.md`.

## Restrições globais

- Código, docs e commits em português do Brasil; identificadores em português.
- Só mexer em: `backend/src/sinais/features/` (arquivos novos + `fs-2`), `backend/src/sinais/modelos/`, `backend/src/sinais/backtest/` (só compatível), testes, `.github/workflows/modelos*.yml`, docs novos e `docs/laboratorio/`. Não editar `pyproject.toml`, `PROGRESSO.md`, `ci.yml`.
- `fs-1` fica intacto (mesmas colunas, mesmo `FEATURE_SET_VERSION`).
- Walk-forward igual à Fase 6: treino 6 meses (1 a cada 3 minutos), calibração 1, teste 1; purga pelo vencimento real; embargo 1 h; holdout final de 3 meses avaliado uma vez; BH; Wilson inf > equilíbrio + 1 p.p.; ≥ 70% dos meses testados acima; supera baselines nas mesmas janelas; holdout com ≥ 100 operações e Wilson inf > equilíbrio. Payout de decisão: 0,86 (equilíbrio 53,76%).
- Nenhum ajuste usa teste ou holdout. Hiperparâmetros do HGB: os da Fase 6 (`HIPERPARAMETROS`), sem busca.
- Apertado = |preço vencimento − preço entrada| ≤ 0,0001 × preço entrada (mesma regra do `simular`).

## Decisões fixadas antes de ver qualquer resultado

1. **Período:** 24 meses (2024-11 a 2026-10), o mesmo da Fase 6, com 1 s em todos eles. Motivo: com 6–9 meses não cabe nem uma dobra (6 + 1 + 1 + 3 = 11 meses). Estimativa: 1 s ≈ 2,6 M linhas/mês; guardamos só tempo + fechamento (16 B/s ≈ 1 GB por ativo em 24 meses) e a tabela por minuto; o resto é descartado mês a mês. A Fase 6 levou 2,3 min por combinação; a v2 deve ficar abaixo de 90 min. O job registra tempo e pico de memória (`/usr/bin/time -v`).
2. **Rótulo:** entrada em segundo inteiro sorteado em `[teto(decisão + 2 s), prazo de compra]`, vencimento `RegraVencimento.vencimento_para(decisão)`, preço = fechamento do candle de 1 s (`SeriePrecos` 1 s). Semente fixa.
3. **Modelo de direção:** treinado só com amostras de treino **não apertadas** (as apertadas são ruído de moeda); calibração isotônica com **todas** as amostras da calibração.
4. **Filtro de apertados:** HGB (mesmos hiperparâmetros) que prevê `apertado` no treino. Limiar escolhido no mês de calibração entre {sem filtro, quantis 0,5 / 0,75 / 0,9 de `p_apertado` da calibração}, pelo maior limite inferior de Wilson da taxa de acerto das decisões que passariam (mínimo 100); empate fica com o menos restritivo.
5. **Candidato à aprovação:** só `fs-2 + filtro` (4 combinações → BH sobre 4). Diagnósticos sem direito a aprovação: `fs-2` sem filtro e `fs-1` com rótulos de 1 s + filtro.
6. **Rodada de fumaça** (só para tempo/memória): 3 meses de 2024-11 a 2025-01 (período só de treino na rodada real), treino 1 mês, sem holdout.
7. Holdout 2026-08 a 2026-10: é o mesmo da Fase 6 (já visto uma vez pela v1). Não há meses novos completos até dezembro; isso é declarado no relatório.

## Revisão — focos

- Mês de 1 s faltando (404) ou com segundos faltando: agregação não quebra, vira NaN e lacuna registrada.
- Tempo em microssegundos (2025+) e em milissegundos (2024) no mesmo período.
- Divisão por zero (minuto sem volume, sem trades, sem mudança de preço) → NaN, nunca inf.
- Agregação mês a mês igual à agregação da série inteira (fronteira de mês).
- Decisão cujo vencimento passa do fim dos dados → rótulo NaN (fora do treino e do teste).

---

### Task 1 (Tarefa): leitura dos klines de 1 s

**Arquivos:** criar `backend/src/sinais/modelos/dados_1s.py`; teste `backend/tests/unit/modelos/test_dados_1s.py`.

**Interfaces — produz:** `ler_zip_1s(conteudo: bytes) -> pd.DataFrame` (índice `abertura` em ms, colunas `o,h,l,c,v,vb,n` float64); `async baixar_mes_1s(http, simbolo, ano, mes) -> pd.DataFrame | None` (None em 404; sem cobertura).

- [ ] Teste: zip sintético com 3 linhas em µs → índice em ms e colunas certas; outro em ms → igual.
- [ ] Ver falhar; implementar com `pd.read_csv` direto do membro do zip (`usecols`); ver passar; commit.

### Task 2 (Tarefa): microestrutura por minuto

**Arquivos:** criar `backend/src/sinais/features/microestrutura.py`; teste `backend/tests/unit/features/test_microestrutura.py`.

**Interfaces — produz:**
- `agregar_segundos(df_1s) -> pd.DataFrame` por minuto (índice = abertura do minuto): `n_seg, v, vb, n, v_ult10, vb_ult10, c_fim, c_s49, c_s29, soma_r2, seg_parados, t_ult_mudanca, seq_fim, vwap`.
- `class AgregadorMicro` com `adicionar(df_1s_mes)` e `resultado() -> pd.DataFrame`; guarda o último minuto do mês anterior para a primeira variação do mês seguinte. Resultado igual a `agregar_segundos` da série inteira.
- `features_microestrutura(agg) -> pd.DataFrame` com colunas `mic_*`: `compra_min, compra_ult10, compra_delta, ret_ult10, ret_ult30, vol_real_bps, vol_real_5m_bps, vol_real_rel15, frac_parados, frac_parados_15, seg_desde_mudanca, explosao_10s, explosao_10s_vs15, sequencia, trades_rel15, vwap_dist, seg_presentes`.
- `JANELA_AO_VIVO_MICRO_MIN = 120`.

- [ ] Testes: minuto conhecido (valores à mão: taxa de compra, retorno dos últimos 10 s, segundos parados, sequência, segundos desde a mudança atravessando minuto); minuto sem volume → NaN, sem inf; agregação em dois pedaços = inteira; janela ao vivo de 120 min reproduz o histórico.
- [ ] Ver falhar; implementar (groupby vetorizado); ver passar; commit.

### Task 3 (Tarefa): conjunto `fs-2` e regressão de vazamento

**Arquivos:** criar `backend/src/sinais/features/fs2.py`; teste `backend/tests/regressao_vazamento/test_causalidade_fs2.py` e `backend/tests/unit/features/test_fs2.py`.

**Interfaces — produz:** `FEATURE_SET_VERSION_FS2 = "fs-2"`; `features_calendario(indice) -> DataFrame` (`cal_hora`, `cal_min_hora`, `cal_dia_semana`); `combinar_fs2(fs1: DataFrame, micro: DataFrame) -> DataFrame` (reindexa micro no índice do fs-1, float32 opcional); `montar_snapshot_fs2(df_1m, df_1s) -> DataFrame`.

- [ ] Testes: colunas = fs-1 ∪ mic_* ∪ cal_*; fs-1 inalterado; linha t igual com 1 s cortado no fim do minuto t; linha t igual com futuro de 1 s embaralhado.
- [ ] Validar o teste por mutação: trocar um `rolling` por `.shift(-1)` e ver o teste de vazamento falhar; desfazer.
- [ ] Commit.

### Task 4 (Tarefa): rótulos com 1 s

**Arquivos:** modificar `backend/src/sinais/modelos/rotulos.py`; teste `backend/tests/unit/modelos/test_rotulos_1s.py`.

**Interfaces — produz:** `rotular_1s(decisoes: np.ndarray, regra, precos_1s: SeriePrecos, latencia_ms=2000, semente=0, limiar_apertado=1e-4) -> DataFrame[decisao, entrada_t, vencimento_t, alvo, apertado]` (`apertado` float 1/0/NaN).

- [ ] Testes: entradas sempre em segundos inteiros dentro de `[teto(decisão+2 s), prazo]` em 1m e 5m; alvo/apertado batem com `simular(..., entrada_aleatoria)` linha a linha quando a entrada é a mesma; vencimento depois do fim → NaN.
- [ ] Ver falhar; implementar vetorizado; ver passar; commit.

### Task 5 (Tarefa): filtro de apertados

**Arquivos:** criar `backend/src/sinais/modelos/filtro.py`; teste `backend/tests/unit/modelos/test_filtro.py`.

**Interfaces — produz:** `treinar_filtro(x, apertado) -> FiltroApertado` (`.probabilidade(x)`); `escolher_limiar_filtro(p_dir, p_ap, alvo, limiar, quantis=(0.5, 0.75, 0.9), n_minimo=100) -> float` (`inf` = sem filtro).

- [ ] Testes: quando as decisões com p_ap alto são moeda e as outras acertam, escolhe um quantil; quando tudo é igual, devolve `inf`; poucos casos → `inf`.
- [ ] Ver falhar; implementar; ver passar; commit.

### Task 6 (Tarefa): avaliação walk-forward v2

**Arquivos:** criar `backend/src/sinais/modelos/avaliacao_v2.py`; teste `backend/tests/unit/modelos/test_avaliacao_v2.py`.

**Interfaces — consome:** Tarefas 4 e 5; `mascara_periodo`, `sinais_do_modelo`, `BASELINES`, `ResultadoCombinacao` (Fase 6). **Produz:** `avaliar_combinacao_v2(df_1m, snapshot, precos_1s, expiracao, payout, ...) -> ResultadoV2` com `principal`, `sem_filtro` (ResultadoCombinacao), `limiares_filtro: list[float]`, `frac_filtrada: list[float]`.

- [ ] Testes: ponta a ponta com passeio aleatório em 1 s → Wilson inf abaixo do equilíbrio, baselines presentes; série com sinal plantado nas features → taxa > 60%; operações de teste e holdout simuladas com 1 s e entrada sorteada (entrada_t não alinhada ao minuto).
- [ ] Ver falhar; implementar; ver passar; commit.

### Task 7 (Tarefa): relatório e linha de comando v2 + workflow

**Arquivos:** criar `backend/src/sinais/modelos/decisao_v2.py`, `.github/workflows/modelos-v2.yml`; teste `backend/tests/unit/modelos/test_decisao_v2.py`.

**Interfaces — produz:** `gerar_markdown_v2(linhas, diagnosticos: dict[str, list[LinhaDecisao]], extras, hipoteses) -> str`; CLI `python -m sinais.modelos.decisao_v2 --meses 24 --fim AAAA-MM --payout 0.86 --treino-meses 6 --holdout-meses 3 --saida relatorio`.

- [ ] Teste do markdown (tabela principal com apertados e holdout; diagnósticos marcados como "sem direito a aprovação").
- [ ] Workflow: `workflow_dispatch` + gatilho `push` temporário no ramo com filtro de caminho; timeout 300; `/usr/bin/time -v`; artefato.
- [ ] Rodada de fumaça; depois a rodada real; baixar o relatório.

### Task 8 (Tarefa): documentação, limpeza e PR

- [ ] `docs/laboratorio/2026-11-25-modelo-v2-payout-86.md` (relatório real) e `docs/fases/fase-06b-modelo-v2.md` (resultado honesto).
- [ ] Remover o gatilho `push` do workflow; suíte, mypy e ruff verdes; push; PR; CI verde. Não fazer merge.
