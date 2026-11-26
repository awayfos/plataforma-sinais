# Pré-registro do Motor de Situações (Fase 6c)

- **Data:** 2026-11-26, **antes** de qualquer contagem de ocorrências ou rodada rotulada com dados reais.
- **Design:** `docs/superpowers/specs/2026-11-26-motor-situacoes-design.md` (§4, §5, §6, §9b, §9c).
- **Código:** os números abaixo são as constantes de `backend/src/sinais/situacoes/parametros.py` neste
  commit. Os detectores estão em `situacoes/detectores.py` e `situacoes/motor.py`, com testes de
  vazamento validados por mutação.
- **Regra:** depois da contagem nada é afrouxado. Chave com menos de 300 ocorrências nos meses de teste
  sai da avaliação confirmatória. Correção de defeito de código encontrada depois é permitida só se for
  declarada no relatório, com o efeito medido.

## 1. Convenções comuns

| Item | Valor |
|---|---|
| Dados | Binance spot, arquivos mensais `data.binance.vision`: klines de 1m (detecção) e de 1 s (entrada e liquidação), BTCUSDT e ETHUSDT, 2024-11 a 2026-10 |
| Candles | Só fechados. 5m e 15m = agregação de blocos **completos** de 1m; o detector usa o último bloco já fechado na decisão (bloco com idade ≥ 1 duração = lacuna, não usado) |
| Decisão | Fechamento do candle de 1m de confirmação |
| Pressão compradora | `vb / v` do candle (volume taker buy / volume). Volume zero = indefinida, nunca satisfaz condição |
| ATR | ATR(14) de Wilder no tempo gráfico indicado |
| Janela de contexto | 4 h (240 candles de 1m; 16 de 15m) |
| Espelho | "topo" e "fundo": regras refletidas (preço invertido; pressão `p` ↔ `1 − p`). Testado: espelhar a série espelha os eventos |
| Conflito (§9b.6) | Evento com outro evento de direção oposta na mesma decisão vira AGUARDAR: fora da contagem, da avaliação e do treino |
| Confluência | Nº de outras variações com a mesma direção em (decisão − 15 min, decisão]. Variável da camada B, não filtro |
| Queda de pressão | sinal × (pressão média dos 5 candles de 1m anteriores − pressão do candle da decisão), sinal +1 topo / −1 fundo |
| Distância a S/R | min(distância à resistência, ao suporte) de `analise/regioes.py` em ATR de 1m |

## 2. Situações (topo descrito; fundo = espelho)

| Variação | Regra exata (topo) | Direção |
|---|---|---|
| **S1** Exaustão no topo novo | Candle *s* com máxima > máxima dos 240 candles anteriores e pressão ≥ 0,55. Confirma no primeiro candle *i* em *s*+1..*s*+10 com fechamento < mínima de *s*, com ≥ 2 dos candles *s*+1..min(*s*+3, *i*) com pressão < 0,50 e nenhuma máxima > máxima de *s* em *s*+1..*i* (nova máxima cancela; nova máxima com pressão ≥ 0,55 abre outro setup) | Venda |
| **S2** Falso rompimento | Níveis = pivôs de 1m (k = 3, entram ao confirmar) fundidos a 0,5 × ATR(1m), com o instante de cada toque. Rompimento no candle *b*: `c[b−1] ≤ P < c[b]` num nível com ≥ 3 toques nas 4 h anteriores (se vários, o de mais toques; empate: o mais perto). Dispara no primeiro candle em *b*+1..*b*+3 que fecha abaixo de P | Venda |
| **S3** Rompimento com força + reteste | Mesmos níveis. Rompimento com ≥ 3 toques em 4 h, volume relativo (20) ≥ 1,5 e pressão ≥ 0,60. Até 15 candles depois: algum candle com mínima > P + 0,25 × ATR (afastou-se) e depois um candle com mínima ≤ P + 0,25 × ATR e fechamento > P (reteste que segura) → dispara. Fechamento ≤ P antes disso cancela | Compra (a favor) |
| **S3b** (§9c) | S3 com ≥ 4 toques (região gasta) | Compra |
| **S4** Reteste após BOS no 5m | BOS de alta no 5m (`analise/estrutura.py`, k = 3); nível = topo rompido. Nos 60 min seguintes ao fechamento do 5m: algum candle de 1m afastou-se (mínima > nível + 0,25 × ATR(1m)); depois um candle com mínima ≤ nível + 0,25 × ATR, fechamento > nível e engolfo de alta ou pin bar de alta → dispara. Fechamento < nível cancela | Compra (a favor) |
| **S5** CHoCH após tendência esgotada | CHoCH de baixa no 5m (k = 3). No último 15m fechado: ADX(14) ≥ 25 e +DI > −DI. Divergência: os dois últimos topos de 5m confirmados com o mais novo mais alto e RSI(14, 5m) menor no candle do pivô; pivô mais novo a ≤ 36 candles de 5m do CHoCH. Decisão no fechamento do 5m do CHoCH | Venda |
| **S6** Rejeição repetida na máxima | No fechamento de cada 15m, janela dos últimos 16 blocos de 15m contíguos: M = máxima; zona = [M − 0,15 × ATR(15m), M]. Toque = bloco com máxima na zona; sequências de blocos consecutivos contam como 1 toque. Todo toque precisa ter fechado abaixo da zona e o último bloco não pode tocar. S6: ≥ 3 toques prévios (o novo é o 4º ou mais). No bloco seguinte, no 1m: primeiro candle com máxima na zona, fechamento abaixo da zona e pressão < 0,50, sem o bloco ter passado de M + 0,15 × ATR(15m) → dispara | Venda |
| **S6a** (§9c) | S6 com 1–2 toques prévios (o novo é o 2º ou 3º toque) | Venda |
| **S7** Divergência no extremo | Topo de 15m (pivô k = 2, entra ao confirmar) mais alto que o topo anterior (a ≤ 32 blocos) com RSI(14) ou histograma do MACD(12,26,9) menor no candle do pivô. Nos 15 min após a confirmação: primeiro candle de 1m com pressão dos últimos 5 candles (Σvb/Σv) < 0,45 e fechamento ≥ topo − 1,0 × ATR(15m); máxima acima do topo cancela | Venda |
| **S8** Extremo de lateralização | No fechamento de cada 15m: ADX(14) < 20 e faixa dos últimos 16 blocos com largura entre 2 e 8 × ATR(15m). No bloco seguinte, no 1m: máxima ≥ topo − 10% da largura, fechamento abaixo disso e pressão < 0,50, sem o bloco ter passado de topo + 10% da largura → dispara (uma vez por lado por bloco) | Venda (para o meio) |

Variações: S3/S3b e S6/S6a (pedido do cliente, §9c); as demais têm uma variação só. Total: 10 variações
× 2 espelhos × 2 ativos × 3 expirações = **120 chaves da camada A**.

## 3. Execução e liquidação (§9b.1)

| Item | Valor |
|---|---|
| Entrada | Segundo inteiro entre decisão + 2 s e decisão + 10 s, sorteado por hash do instante da decisão com semente 7 (resultado independente do lote) |
| Tolerância | Não entra se \|preço na entrada − preço na decisão\| > 0,5 × ATR(14) de 1m (`FORA_DA_TOLERANCIA`) |
| Vencimento | Alinhado ao relógio da Exnova; válido só se vencimento − decisão ≤ grade e a entrada cair até o prazo de compra (`FORA_DA_JANELA`). Tempo restante registrado |
| Expirações | 15 min (principal; corte 5 min, confirmado), 5 min (corte 100 s, hipótese), 30 min (corte 10 min, hipótese) |
| Preço | Fechamento do candle de 1 s que termina no instante; sem preço = `SEM_DADO` |
| Resultado | WIN/LOSS/EMPATE; empate fora da taxa (como Fases 6 e 6b); apertado = \|Δ\| ≤ 0,01% (diagnóstico) |
| Sobreposição | Um sinal ativo por variação × espelho × ativo × expiração (um por vencimento) |
| Payout | 0,86 → equilíbrio p* = 53,76% |

## 4. Contagem sem rótulo (este pré-registro vem antes dela)

Por chave: eventos sem conflito, janela válida, um por vencimento, sem olhar preço. Períodos: **teste**
= meses de teste do walk-forward (2025-06 a 2026-07, 14 meses), **holdout** = 2026-08 a 2026-10,
**total** = 2024-11 a 2026-10. **Corte: n(teste) ≥ 300**; abaixo disso a chave sai da avaliação
confirmatória (é só reportada como diagnóstico).

## 5. Avaliação

**Walk-forward:** dobras mensais da Fase 6/6b sobre 2024-11..2026-10 — treino 6 meses, calibração 1,
teste 1, holdout final 2026-08..10 (já visto pela Fase 6; declarado), purga pelo vencimento real e
embargo de 1 h.

**Camada A (regra pura):** cada chave elegível simulada (§3) nos 14 meses de teste agregados e, à parte,
no holdout. Critérios (§13.3), todos obrigatórios:

1. n ≥ 300 operações decididas (WIN + LOSS) nos meses de teste;
2. Wilson inferior 95% > p* + 1 p.p. (54,76%);
3. taxa acima de cada estratégia simples nos mesmos meses e com a mesma execução: comprar sempre, vender
   sempre, seguir o último candle e aleatória com a mesma frequência de sinais da chave;
4. ≥ 70% dos 14 meses de teste com ≥ 10 operações decididas **e** taxa > p* (mês com menos de 10 conta
   como abaixo);
5. Benjamini-Hochberg (q = 0,05) sobre a família inteira: as 120 chaves A + todas as chaves B tentadas;
   p-valor binomial unilateral contra p*; chave inelegível entra com p = 1;
6. holdout: ≥ 50 operações decididas e taxa > p* (critério mais fraco que o da Fase 6, porque situações
   são raras; a confirmação de verdade é em meses novos, §7).

**Camada B (§5, §9b.5):** um modelo por variação × expiração, juntando espelhos e ativos.

- Linhas de treino = eventos sem conflito com WIN/LOSS, simulados um a um (sem a regra de sobreposição),
  com vencimento ≤ início da calibração − 1 h. Só é tentada se **toda** dobra (14 + holdout) tiver
  ≥ 1.000 linhas de treino; senão, não é tentada (e não entra na família).
- Variáveis: `fs-2` do minuto da decisão + `ordem_toque`, `min_entre_toques`, `dist_sr_atr`,
  `queda_pressao`, `confluencias`, espelho (0/1), ativo (0/1), direção e tempo restante até o vencimento.
- Modelo: HistGradientBoosting com os hiperparâmetros da Fase 6 (sem busca) + calibração isotônica por
  validação cruzada temporal (`TimeSeriesSplit`, 3 partes) dentro do bloco de treino. Alvo: a direção da
  situação vence.
- Limiar: no mês de calibração (eventos com vencimento ≤ início do teste − 1 h), entre p* + 1, + 3 e
  + 5 p.p., o de maior Wilson inferior entre os eventos com p ≥ limiar, exigindo ≥ 30 decididos; sem
  nenhum válido, p* + 1 p.p.
- Sinais B = eventos da chave no mês de teste com p ≥ limiar, simulados como A (§3).
- Critérios: os mesmos 1–6 de A. **B só é adotada** se passar e superar A nos mesmos meses de teste:
  teste de duas proporções unilateral (taxa B > taxa A), p < 0,05.

**Resultado:** chave aprovada na descoberta (A, ou B adotada) vira **candidata**. Nenhum sinal é
liberado sem a confirmação em meses novos.

## 6. Proibido depois deste commit

Mudar qualquer número das seções 1–5, acrescentar variação, trocar o corte de 300, trocar critérios,
escolher limiar olhando teste/holdout ou rodar de novo com outra semente.

## 7. Confirmação em meses novos (§9b.2)

- Meses fechados a partir de **2026-11**, reprocessados dos arquivos mensais da Binance assim que cada mês
  é publicado, com o mesmo código e os mesmos parâmetros (`python -m sinais.situacoes.confirmacao`).
  Cada execução reprocessa todos os meses novos desde 2026-11 (resultado acumulado e reproduzível).
- Família própria (separada da Fase 6b e da descoberta): as chaves candidatas da §5.
- Critério por candidata: n ≥ 100 operações decididas não sobrepostas nos meses novos **e** Wilson
  inferior > p*; Benjamini-Hochberg (q = 0,05) sobre as candidatas.
- Sinais do último dia de cada mês cujo vencimento cai no mês seguinte ficam `SEM_DADO` (o mês seguinte
  ainda não foi publicado). Efeito: perda de no máximo 30 min por mês.
- Chaves não candidatas também são reprocessadas, só como diagnóstico, sem direito a aprovação.
