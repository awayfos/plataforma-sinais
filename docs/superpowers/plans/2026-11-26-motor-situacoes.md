# Motor de Situações (pesquisa) — plano de implementação

> **Para agentes:** SUB-SKILL OBRIGATÓRIA: superpowers:executing-plans (execução nativa, decidida pelo
> coordenador), com superpowers:test-driven-development e superpowers:verification-before-completion.
> Passos com caixas (`- [ ]`).

**Objetivo:** construir o motor de pesquisa de situações (S1–S8 + espelhos + variações), medir cada
situação com a regra real da Exnova e entrada em 1 s, avaliar camada A (regra pura) e camada B (IA
qualificadora) em walk-forward com os critérios §13.3, e deixar pronta a ferramenta de confirmação em
meses novos.

**Arquitetura:** pacote novo `sinais/situacoes/`, puro e causal: uma *base* por ativo (1m + quadros
fechados de 5m/15m, ATR, pressão), detectores que devolvem eventos num `DataFrame` de esquema fixo,
simulação vetorizada com sorteio de entrada independente do lote, avaliação A/B por chave
`variação × espelho × ativo × expiração`. Reusa `analise/*`, `features/*` (fs-2), `backtest/metricas`,
`backtest/walk_forward`, `corretoras/regras`, `modelos/treino` (hiperparâmetros) e `modelos/dados_1s`.
Nada do ramo 06b é alterado.

**Pilha:** Python 3.13, pandas, numpy, scikit-learn (HGB + isotônica), pytest, mypy estrito, ruff.

**Spec:** `docs/superpowers/specs/2026-11-26-motor-situacoes-design.md` (autoridade), com
`2026-11-25-plataforma-sinais-design.md` §12–§13 e `docs/fases/fase-06b-modelo-v2.md` §7.

## Restrições globais

- Código, docs e commits em português; identificadores em português.
- Só candles **fechados**; quadros maiores pelo último bloco completo já fechado (como `montar_snapshot`).
- Todos os números de S2–S8 (≤ 2 variações cada) ficam em `situacoes/parametros.py` e no documento
  `docs/laboratorio/2026-11-26-situacoes-pre-registro.md`, commitados **antes** de qualquer contagem.
- Depois da contagem nada é afrouxado; chave com < 300 ocorrências nos meses de teste sai da avaliação
  confirmatória.
- Entrada: segundo inteiro sorteado em decisão + 2..10 s; recusa se |preço entrada − preço decisão| >
  0,5 × ATR14(1m); vencimento alinhado ao relógio; válido só se `vencimento − decisão ≤ grade` e
  entrada ≤ prazo de compra. Payout 0,86 (p* = 53,76%). Expirações 15m (principal), 5m, 30m.
- Walk-forward 2024-11..2026-10, 6/1/1, holdout 2026-08..10 (já visto na Fase 6; declarado).
- Suíte, `mypy` e `ruff check`/`ruff format --check` verdes a cada commit.
- Rodadas reais só no GitHub Actions; relatório impresso no log.

## Foco de revisão

1. Lacunas nos dados (minutos faltando): a base não pode juntar blocos de 15m incompletos nem usar o bloco
   em formação como fechado → teste de lacuna em `test_base.py`.
2. Volume zero (pressão indefinida): nenhum detector dispara com pressão NaN → teste em `test_detectores_*.py`.
3. Vencimento depois do fim dos dados (fim de mês na confirmação): `SEM_DADO`, nunca WIN/LOSS → teste em
   `test_simulacao.py`.
4. Sorteio da entrada dependente do lote (mês a mês × série inteira): mesmo resultado → teste em
   `test_simulacao.py`.
5. Situações opostas no mesmo minuto: as duas viram conflito (AGUARDAR) e não entram em contagem nem
   avaliação → teste em `test_detectar_todas.py`.

---

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `situacoes/parametros.py` | Constantes pré-registradas (dataclasses congeladas) e lista `VARIACOES` |
| `situacoes/base.py` | `Base`, `montar_base(df_1m)`: arrays 1m, pressão, ATR, quadros 5m/15m fechados e mapa 1m→último bloco fechado |
| `situacoes/eventos.py` | Esquema `COLUNAS_EVENTO`, `quadro_eventos(lista)` |
| `situacoes/zonas.py` | `Zonas`: níveis de pivôs de 1m com instantes dos toques (toques em 4 h, ordem, tempo entre toques) |
| `situacoes/detectores.py` | `detectar_s1` … `detectar_s8` |
| `situacoes/motor.py` | `detectar_todas(df_1m)`: roda tudo, contexto comum, confluências e conflitos |
| `situacoes/simulacao.py` | `simular_eventos`, `deslocamento_entrada` |
| `situacoes/liquidacao.py` | `RegistroSinal`, `liquidar_sinal` (registro da área de sinais) |
| `situacoes/contagem.py` | `contar_ocorrencias` + Markdown |
| `situacoes/avaliacao.py` | Camada A, baselines, critérios, BH, teste "B supera A" |
| `situacoes/qualificadora.py` | Camada B (treino por situação, limiar na calibração) |
| `situacoes/features_b.py` | fs-2 só nas linhas dos eventos + colunas de contexto |
| `situacoes/relatorio.py` | CLI `--modo contagem|avaliacao` (baixa dados, roda, imprime) |
| `situacoes/confirmacao.py` | CLI de confirmação em meses novos (≥ 2026-11) |
| `tests/unit/situacoes/*` | Testes unitários |
| `tests/regressao_vazamento/test_causalidade_situacoes.py` | Truncamento + futuro embaralhado |
| `.github/workflows/situacoes.yml` | Rodadas reais (gatilho `push` temporário) e confirmação mensal |

Esquema do evento (`COLUNAS_EVENTO`): `decisao` (int ms, fechamento do candle 1m), `situacao` ("S1"…"S8"),
`variacao` ("S1","S2","S3","S3b","S4","S5","S6","S6a","S7","S8"), `espelho` ("topo"|"fundo"),
`direcao` (+1/−1), `nivel` (preço de referência), `ordem_toque`, `min_entre_toques`, `dist_sr_atr`,
`queda_pressao` (float, NaN se não se aplica), `confluencias` (int), `conflito` (bool).

---

### Task 1: parâmetros, esquema de eventos e base multi-tempo

**Files:** Create `situacoes/{__init__,parametros,eventos,base}.py`; Test `tests/unit/situacoes/{__init__,sinteticos,test_base}.py`

**Interfaces — Produces:**
- `Base` (dataclass): `t` (aberturas 1m, int64), `decisao = t + 60 000`, `o,h,l,c,v` (float64), `pressao`
  (vb/v, NaN se v = 0), `atr1` (ATR14 1m), `vol_rel` (volume_relativo n=20), `q5`, `q15` (`Quadro`: aberturas,
  o,h,l,c,v,vb, mais colunas calculadas) e `idx5`, `idx15` (para cada linha 1m, posição do último bloco
  fechado até a decisão, −1 se nenhum ou vencido).
- `montar_base(df_1m: pd.DataFrame) -> Base`.

- [ ] Teste: `idx15` da linha 1m que fecha às 00:15 aponta para o bloco 00:00; a de 00:14 para o bloco anterior; bloco com minuto faltando não existe; contexto mais velho que 1 duração vira −1.
- [ ] Teste: `pressao` é NaN com `v == 0`.
- [ ] Implementar (agregação via `features.snapshot.agregar_quadro`; mapa via `searchsorted` do fechamento).
- [ ] Rodar, passar, commit `feat(situacoes): parâmetros, eventos e base multi-tempo`.

### Task 2: zonas com toques no tempo

**Files:** Create `situacoes/zonas.py`; Test `tests/unit/situacoes/test_zonas.py`

**Produces:** `Zonas(tolerancia_atr=0.5, maximo=60)`, `.adicionar(preco, tol, t_ms)`,
`.rompidas(c_ant, c_atual, t_ms, janela_ms) -> list[Nivel]` (níveis com `c_ant ≤ P < c_atual`, alta, ou
`c_ant ≥ P > c_atual`, baixa), `Nivel(preco, toques: list[int])`, `toques_em(nivel, t, janela) -> int`,
`min_entre_toques(nivel, t, janela) -> float`.

- [ ] Testes: fusão dentro da tolerância soma toque; toques mais velhos que 4 h não contam; rompimento de alta e de baixa; minutos entre os dois últimos toques.
- [ ] Implementar, passar, commit.

### Task 3: detectores S1, S2, S3/S3b

**Files:** Create `situacoes/detectores.py`; Test `tests/unit/situacoes/test_detectores_s1_s3.py`

**Produces:** `detectar_sN(base: Base, p: ParamSN) -> list[dict]` (linhas de evento com as colunas do
esquema, exceto `dist_sr_atr`, `queda_pressao`, `confluencias`, `conflito`, preenchidas pelo motor).
Regras exatas: as do pré-registro (Task 7). Cada teste monta um cenário mínimo com `sinteticos.py`.

- [ ] Para cada detector: um cenário que dispara no minuto esperado (direção e espelho certos) e um que não dispara (condição-chave faltando; para S1 também nova máxima antes da confirmação; pressão NaN).
- [ ] Implementar, passar, commit.

### Task 4: detectores S4, S5

Mesmo formato (`test_detectores_s4_s5.py`): BOS 5m + reteste + rejeição (engolfo/pin bar); CHoCH 5m
com ADX 15m e divergência de RSI 5m.

### Task 5: detectores S6/S6a, S7, S8

Mesmo formato (`test_detectores_s6_s8.py`): zona de máximas de 15m com ordem do toque (S6 ≥ 4º, S6a
2º–3º); topo de 15m com divergência RSI/MACD e inversão de pressão; extremo de lateralização.

### Task 6: motor (contexto comum, confluência, conflito), simetria e vazamento

**Files:** Create `situacoes/motor.py`; Test `tests/unit/situacoes/test_detectar_todas.py`,
`tests/regressao_vazamento/test_causalidade_situacoes.py`

**Produces:** `detectar_todas(df_1m: pd.DataFrame, variacoes=VARIACOES) -> pd.DataFrame` ordenado por
`decisao`: `dist_sr_atr = min(reg res_dist, sup_dist)` de `analise.regioes`; `queda_pressao = sinal ×
(média da pressão dos 5 candles anteriores − pressão do candle da decisão)` (sinal +1 topo, −1 fundo);
`confluencias` = nº de outras variações com a mesma direção e decisão em (d − 15 min, d];
`conflito` = existe evento de direção oposta com a mesma `decisao`.

- [ ] Teste de conflito (Foco 5) e de confluência.
- [ ] Teste de simetria: espelhar o preço (2K − x, troca h↔l, vb → v − vb) troca topo↔fundo e direção com os mesmos instantes.
- [ ] Vazamento: para instantes sorteados, eventos com `decisao ≤ t` iguais com a série cortada em t e com o futuro embaralhado; cobertura: o sintético dispara todas as variações antes dos cortes.
- [ ] Validação por mutação (registrar no doc da fase): `h[k+1]` em S1, bloco de 15m em formação em S6, pivô sem atraso em S7, pressão do candle seguinte no motor → os testes falham; reverter.
- [ ] Commit.

### Task 7: simulação, liquidação, contagem e **commit de pré-registro**

**Files:** Create `situacoes/{simulacao,liquidacao,contagem}.py`, `docs/laboratorio/2026-11-26-situacoes-pre-registro.md`; Tests `test_simulacao.py`, `test_liquidacao.py`, `test_contagem.py`

**Produces:**
- `deslocamento_entrada(decisoes: np.ndarray, semente: int) -> np.ndarray` (s ∈ 2..10, por hash do segundo da decisão: independente do lote).
- `simular_eventos(eventos, precos_1s: SeriePrecos, regra: RegraVencimento, atr_por_decisao: pd.Series, semente=7, sem_sobreposicao=True, tolerancia_atr=0.5) -> pd.DataFrame` com `decisao, direcao, entrada_t, vencimento_t, tempo_restante_s, preco_decisao, preco_entrada, preco_vencimento, apertado, resultado` (`WIN/LOSS/TIE/FORA_DA_JANELA/FORA_DA_TOLERANCIA/SEM_DADO/IGNORADO_ATIVO`).
- `RegistroSinal` e `liquidar_sinal(ativo, direcao, expiracao_min, entrada_t, preco_entrada, vencimento_t, precos_1s) -> RegistroSinal` (`WIN/LOSS/EMPATE/SEM_DADO`); `registros_de(ops, ativo, expiracao_min)`.
- `contar_ocorrencias(eventos, regra, inicio, fim) -> int` (sem conflito, janela válida, um por vencimento) e `tabela_contagem(...) -> pd.DataFrame`.

- [ ] Testes: janela (15m: decisão às :40 inválida, às :30 válida com 14:5x restantes); tolerância; empate; `SEM_DADO` após o fim (Foco 3); lote mês a mês = série inteira (Foco 4); registro igual ao da simulação.
- [ ] Escrever o documento de pré-registro com todos os números; commit `docs(laboratorio): pré-registro do motor de situações` **antes** de rodar a contagem.

### Task 8: rodada de contagem (sem rótulo)

`relatorio.py --modo contagem` (só 1m) + `.github/workflows/situacoes.yml`; rodar no Actions, copiar a
tabela para `docs/laboratorio/2026-11-26-situacoes-contagem.md`, commit. Lista de chaves elegíveis fica
fixada nesse commit.

### Task 9: camada A, baselines, critérios e BH

**Files:** `situacoes/avaliacao.py`; Test `test_avaliacao.py`

**Produces:** `meses_teste(inicio, fim) -> list[(ini, fim)]` (dobras 6/1/1, holdout 3);
`avaliar_a(ops_por_chave, baselines, payout, meses) -> list[LinhaSituacao]`;
`meses_acima(ops, p_eq, meses, minimo=10)`; `teste_duas_proporcoes(wa, na, wb, nb) -> float` (unilateral);
`consolidar_familia(linhas) -> list[LinhaSituacao]` (BH sobre A + B, p = 1 para inelegíveis).

- [ ] Testes de cada critério isolado, BH com chave inelegível, B supera A.
- [ ] Commit.

### Task 10: camada B

**Files:** `situacoes/qualificadora.py`, `situacoes/features_b.py`; Tests `test_qualificadora.py`, `test_features_b.py`

**Produces:** `snapshot_fs2_nas_linhas(df_1m, micro, linhas) -> pd.DataFrame` (igual ao `montar_snapshot_em_blocos` nessas linhas); `treinar_qualificadora(x, y, tempos) -> ModeloCalibrado` (HGB `HIPERPARAMETROS` + `CalibratedClassifierCV(isotonic, cv=TimeSeriesSplit(3))`); `escolher_limiar(p, y, p_eq) -> float`; `avaliar_b(...)`.

- [ ] Teste: snapshot nas linhas = snapshot completo nessas linhas; com sinal plantado no contexto, B supera A; < 1000 linhas → não tentada.
- [ ] Commit.

### Task 11: rodada de avaliação real e relatório

`relatorio.py --modo avaliacao`; rodar no Actions; `docs/laboratorio/2026-11-26-situacoes-resultado.md`.

### Task 12: confirmação em meses novos

`situacoes/confirmacao.py` (reprocessa todos os meses fechados ≥ 2026-11 com o mesmo código; critério
n ≥ 100 e Wilson inf. > p*; família própria; imprime registros por sinal). Teste com dados sintéticos e
fonte falsa. Agendamento mensal no workflow (dia 2, só na `main`).

### Task 13: documentação, limpeza e PR

`docs/fases/fase-06c-situacoes.md`; remover gatilho `push` temporário; suíte/mypy/ruff verdes; PR para a
`main` (depende do #15), CI verde, sem merge.
