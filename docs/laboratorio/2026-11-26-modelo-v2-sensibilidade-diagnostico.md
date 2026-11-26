# DIAGNÓSTICO DE SENSIBILIDADE (sem direito a aprovação) — modelo v2 (Fase 6b)

Variação avaliada: entrada sorteada entre decisão + 2 s e decisão + 10 s; tolerância de preço na entrada de 0.5 x ATR(14) de 1m. Os critérios de aprovação são calculados só para leitura; nada aqui liga uma combinação.

## Hipóteses e fonte

- **fonte:** data.binance.vision, klines de 1m e 1s, 2024-11 a 2026-10 (24 meses; segundos por ativo: {'BTCUSDT': 63072000, 'ETHUSDT': 63072000})
- **modelo:** HistGradientBoosting (hiperparâmetros da Fase 6, sem busca) + calibração isotônica; features fs-2 = fs-1 + 17 de microestrutura de 1 s + 3 de calendário
- **rótulo:** entrada num segundo sorteado entre decisão + 2 s e decisão + 10 s (nota posterior: o texto impresso nesta rodada dizia "e o prazo de compra", mas o código já aplicava o limite de 10 s também aos rótulos; a frase do relatório foi corrigida depois); vencimento alinhado ao relógio da Exnova; preço = fechamento do candle de 1 s
- **treino da direção:** só amostras de treino não apertadas
- **calibração:** mês de calibração dividido em duas metades purgadas (embargo de 1 h): isotônica na primeira; limiar do filtro na segunda
- **filtro de apertados:** HGB prevê apertado (|Δ| ≤ 0,01%); limiar escolhido na 2ª metade da calibração entre sem filtro e cortar os 10%/25%/50% mais prováveis (maior Wilson inf.)
- **execução:** entrada sorteada entre decisão + 2 s e decisão + 10 s; tolerância de preço na entrada de 0.5 x ATR(14) de 1m
- **walk-forward:** treino 6 meses (1 a cada 3 minutos) → calibração 1 mês → teste 1 mês; purga pelo vencimento real e embargo de 1 h; holdout final de 3 meses avaliado uma vez
- **simulação:** teste, holdout e estratégias simples com 1 s e entrada sorteada (semente 7); um sinal ativo por vez
- **decisão:** COMPRA se p ≥ equilíbrio + 1 p.p.; VENDA se p ≤ 1 − (equilíbrio + 1 p.p.)
- **payout:** 0.86 (caso de decisão: menor payout informado da Exnova)
- **cortes:** 1m: 30 s (confirmado); 5m: 100 s (hipótese de 1/3 da grade)
- **lacunas:** nenhuma

## Resultado do candidato (fs-2 + filtro de apertados)

| Ativo | Exp. | Operações | Taxa | Wilson inf. | Equilíbrio | Melhor simples | Meses acima | Apertados | Taxa s/ apertados | Holdout: operações | Holdout: taxa | Holdout: Wilson inf. | Holdout: apertados | ECE | Dobras | Recomendação | Motivo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BTCUSDT | 1m | 23447 | 54.59% | 53.95% | 53.76% | 50.50% | 64.29% | 38.73% | 54.68% | 3350 | 52.63% | 50.93% | 19.68% | 0.85% | 14 | (teria: não ligar) | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| BTCUSDT | 5m | 8369 | 52.83% | 51.76% | 53.76% | 50.43% | 28.57% | 10.96% | 53.54% | 907 | 50.17% | 46.92% | 22.41% | 0.92% | 14 | (teria: não ligar) | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| ETHUSDT | 1m | 19962 | 53.58% | 52.89% | 53.76% | 50.43% | 57.14% | 16.08% | 54.26% | 7199 | 54.40% | 53.24% | 32.62% | 0.82% | 14 | (teria: não ligar) | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| ETHUSDT | 5m | 22927 | 55.04% | 54.40% | 53.76% | 50.08% | 92.86% | 8.78% | 55.50% | 7504 | 54.12% | 52.99% | 9.55% | 1.28% | 14 | (teria: não ligar) | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |

Apertados: fração das operações liquidadas com |Δ preço| ≤ 0,01%. Fora da amostra = dobras do walk-forward agregadas; holdout = últimos meses, avaliados uma vez.

## Filtro de apertados (escolhido só na calibração)

| Ativo | Exp. | Dobras de teste com filtro | Fração média cortada no teste | Limiares no teste | Limiar no holdout | Fração cortada no holdout |
|---|---|---|---|---|---|---|
| BTCUSDT | 1m | 5 de 14 | 17.64% | —, —, —, —, —, —, —, —, —, 0.324, 0.200, 0.250, 0.443, 0.224 | 0.306 | 60.92% |
| BTCUSDT | 5m | 7 de 14 | 15.72% | —, 0.302, —, 0.286, —, 0.154, —, —, 0.205, 0.091, 0.095, 0.122, —, — | — | 0.00% |
| ETHUSDT | 1m | 10 de 14 | 21.24% | 0.115, 0.260, 0.193, —, 0.269, 0.145, 0.169, 0.432, —, —, —, 0.206, 0.340, 0.303 | — | 0.00% |
| ETHUSDT | 5m | 8 de 14 | 15.21% | 0.059, 0.068, —, 0.061, 0.163, —, —, 0.205, 0.206, —, 0.160, —, —, 0.158 | 0.203 | 17.65% |

## Diagnóstico: fs-2 sem filtro (sem direito a aprovação)

Mesmo walk-forward e mesmas janelas; serve só para entender o efeito de cada parte.

| Ativo | Exp. | Operações | Taxa | Wilson inf. | Equilíbrio | Melhor simples | Meses acima | Apertados | Taxa s/ apertados | Holdout: operações | Holdout: taxa | Holdout: Wilson inf. | Holdout: apertados | ECE | Dobras | Recomendação | Motivo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BTCUSDT | 1m | 29785 | 54.48% | 53.92% | 53.76% | 50.50% | 64.29% | 39.99% | 54.74% | 7934 | 53.83% | 52.73% | 45.73% | 0.85% | 14 | (teria: não ligar) | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| BTCUSDT | 5m | 10799 | 53.56% | 52.62% | 53.76% | 50.16% | 35.71% | 12.86% | 54.04% | 907 | 50.17% | 46.92% | 22.41% | 0.92% | 14 | (teria: não ligar) | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| ETHUSDT | 1m | 26836 | 53.48% | 52.89% | 53.76% | 50.22% | 50.00% | 19.84% | 54.08% | 7199 | 54.40% | 53.24% | 32.62% | 0.82% | 14 | (teria: não ligar) | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| ETHUSDT | 5m | 26305 | 54.92% | 54.32% | 53.76% | 50.08% | 85.71% | 9.24% | 55.34% | 8779 | 54.22% | 53.18% | 12.79% | 1.28% | 14 | (teria: não ligar) | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |

## Conclusão

Diagnóstico de sensibilidade: não aprova nem reprova combinações. A configuração só pode ser aprovada na rodada confirmatória pré-registrada, em meses novos.

Tempo total: 36.7 min; pico de memória 5777 MB.

Execução: workflow "Modelos v2", run 45760895573, job "sensibilidade" (commit 0f455ab), `--meses 24 --fim 2026-10 --payout 0.86 --entrada-max-s 10 --tolerancia-atr 0.5 --sem-ablacao-fs1`; 37 min, pico de memória 5,9 GB. **Diagnóstico de sensibilidade: não aprova nada.** A configuração só pode ser aprovada na rodada confirmatória pré-registrada (`docs/fases/fase-06b-modelo-v2.md`, seção 7), com meses novos.
