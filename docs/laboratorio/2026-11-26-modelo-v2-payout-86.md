# Relatório de decisão — modelo v2 (Fase 6b)

## Hipóteses e fonte

- **fonte:** data.binance.vision, klines de 1m e 1s, 2024-11 a 2026-10 (24 meses; segundos por ativo: {'BTCUSDT': 63072000, 'ETHUSDT': 63072000})
- **modelo:** HistGradientBoosting (hiperparâmetros da Fase 6, sem busca) + calibração isotônica; features fs-2 = fs-1 + 17 de microestrutura de 1 s + 3 de calendário
- **rótulo:** entrada num segundo sorteado entre decisão + 2 s e o prazo de compra; vencimento alinhado ao relógio da Exnova; preço = fechamento do candle de 1 s
- **treino da direção:** só amostras de treino não apertadas
- **calibração:** mês de calibração dividido em duas metades purgadas (embargo de 1 h): isotônica na primeira; limiar do filtro na segunda
- **filtro de apertados:** HGB prevê apertado (|Δ| ≤ 0,01%); limiar escolhido na 2ª metade da calibração entre sem filtro e cortar os 10%/25%/50% mais prováveis (maior Wilson inf.)
- **execução:** padrão: entrada sorteada em toda a janela de compra, sem tolerância de preço
- **walk-forward:** treino 6 meses (1 a cada 3 minutos) → calibração 1 mês → teste 1 mês; purga pelo vencimento real e embargo de 1 h; holdout final de 3 meses avaliado uma vez
- **simulação:** teste, holdout e estratégias simples com 1 s e entrada sorteada (semente 7); um sinal ativo por vez
- **decisão:** COMPRA se p ≥ equilíbrio + 1 p.p.; VENDA se p ≤ 1 − (equilíbrio + 1 p.p.)
- **payout:** 0.86 (caso de decisão: menor payout informado da Exnova)
- **cortes:** 1m: 30 s (confirmado); 5m: 100 s (hipótese de 1/3 da grade)
- **lacunas:** nenhuma

## Resultado do candidato (fs-2 + filtro de apertados)

| Ativo | Exp. | Operações | Taxa | Wilson inf. | Equilíbrio | Melhor simples | Meses acima | Apertados | Taxa s/ apertados | Holdout: operações | Holdout: taxa | Holdout: Wilson inf. | Holdout: apertados | ECE | Dobras | Recomendação | Motivo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BTCUSDT | 1m | 7132 | 53.74% | 52.58% | 53.76% | 50.25% | 42.86% | 28.30% | 53.74% | 4342 | 52.33% | 50.84% | 46.46% | 0.92% | 14 | **não ligar** | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| BTCUSDT | 5m | 5239 | 52.53% | 51.18% | 53.76% | 50.07% | 57.14% | 14.82% | 53.37% | 3416 | 49.74% | 48.06% | 23.87% | 0.89% | 14 | **não ligar** | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| ETHUSDT | 1m | 10607 | 52.97% | 52.01% | 53.76% | 50.51% | 28.57% | 17.44% | 53.25% | 2530 | 53.87% | 51.93% | 15.11% | 0.91% | 14 | **não ligar** | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| ETHUSDT | 5m | 12843 | 51.45% | 50.59% | 53.76% | 50.21% | 28.57% | 12.53% | 51.61% | 9995 | 51.88% | 50.90% | 15.39% | 1.51% | 14 | **não ligar** | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |

Apertados: fração das operações liquidadas com |Δ preço| ≤ 0,01%. Fora da amostra = dobras do walk-forward agregadas; holdout = últimos meses, avaliados uma vez.

## Filtro de apertados (escolhido só na calibração)

| Ativo | Exp. | Dobras de teste com filtro | Fração média cortada no teste | Limiares no teste | Limiar no holdout | Fração cortada no holdout |
|---|---|---|---|---|---|---|
| BTCUSDT | 1m | 6 de 14 | 15.84% | —, —, —, —, —, 0.497, 0.208, —, —, —, 0.310, 0.534, 0.387, 0.350 | — | 0.00% |
| BTCUSDT | 5m | 9 de 14 | 22.97% | 0.185, 0.354, 0.166, —, —, —, 0.139, 0.159, 0.413, 0.113, 0.121, —, 0.195, — | — | 0.00% |
| ETHUSDT | 1m | 7 de 14 | 14.65% | 0.135, 0.300, 0.219, —, —, —, 0.266, 0.367, 0.319, —, —, —, 0.398, — | 0.247 | 51.76% |
| ETHUSDT | 5m | 5 de 14 | 11.29% | 0.071, —, 0.116, —, 0.203, —, 0.137, —, —, —, —, —, 0.194, — | — | 0.00% |

## Diagnóstico: fs-2 sem filtro (sem direito a aprovação)

Mesmo walk-forward e mesmas janelas; serve só para entender o efeito de cada parte.

| Ativo | Exp. | Operações | Taxa | Wilson inf. | Equilíbrio | Melhor simples | Meses acima | Apertados | Taxa s/ apertados | Holdout: operações | Holdout: taxa | Holdout: Wilson inf. | Holdout: apertados | ECE | Dobras | Recomendação | Motivo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BTCUSDT | 1m | 9563 | 53.21% | 52.20% | 53.76% | 50.40% | 42.86% | 36.19% | 53.63% | 4342 | 52.33% | 50.84% | 46.46% | 0.92% | 14 | (teria: não ligar) | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| BTCUSDT | 5m | 6363 | 51.69% | 50.46% | 53.76% | 50.07% | 42.86% | 17.05% | 51.93% | 3416 | 49.74% | 48.06% | 23.87% | 0.89% | 14 | (teria: não ligar) | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| ETHUSDT | 1m | 13347 | 52.63% | 51.79% | 53.76% | 50.85% | 14.29% | 22.94% | 53.18% | 4993 | 52.57% | 51.19% | 31.16% | 0.91% | 14 | (teria: não ligar) | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| ETHUSDT | 5m | 13837 | 51.93% | 51.09% | 53.76% | 50.21% | 50.00% | 12.67% | 51.91% | 9995 | 51.88% | 50.90% | 15.39% | 1.51% | 14 | (teria: não ligar) | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |

## Diagnóstico: fs-1 + filtro, rótulos de 1 s (sem direito a aprovação)

Mesmo walk-forward e mesmas janelas; serve só para entender o efeito de cada parte.

| Ativo | Exp. | Operações | Taxa | Wilson inf. | Equilíbrio | Melhor simples | Meses acima | Apertados | Taxa s/ apertados | Holdout: operações | Holdout: taxa | Holdout: Wilson inf. | Holdout: apertados | ECE | Dobras | Recomendação | Motivo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BTCUSDT | 1m | 9161 | 52.20% | 51.18% | 53.76% | 50.25% | 35.71% | 34.13% | 52.63% | 1092 | 53.02% | 50.06% | 25.91% | 0.86% | 14 | (teria: não ligar) | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| BTCUSDT | 5m | 5748 | 51.01% | 49.72% | 53.76% | 50.28% | 7.14% | 14.33% | 51.48% | 2519 | 50.50% | 48.54% | 17.03% | 1.01% | 14 | (teria: não ligar) | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| ETHUSDT | 1m | 13857 | 53.08% | 52.25% | 53.76% | 50.07% | 21.43% | 16.60% | 53.46% | 2597 | 54.29% | 52.37% | 26.94% | 0.91% | 14 | (teria: não ligar) | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| ETHUSDT | 5m | 13210 | 52.22% | 51.37% | 53.76% | 50.21% | 21.43% | 10.19% | 52.46% | 3458 | 51.42% | 49.75% | 8.23% | 1.40% | 14 | (teria: não ligar) | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |

## Conclusão

Nenhuma combinação passou nos critérios. Pela regra do produto, todas mostram AGUARDAR até que um modelo seja aprovado.

Tempo total: 59.0 min; pico de memória 6678 MB.

Execução: workflow "Modelos v2", run 45760895573, job "principal" (commit 0f455ab), `--meses 24 --fim 2026-10 --payout 0.86`; 59 min, pico de memória 6,8 GB (`/usr/bin/time -v`: 6.838.028 kB). Relatório copiado do log do job. Substitui a primeira rodada (run 45647410250, commit 9c28b3a), feita antes da correção que separou a calibração isotônica e a escolha do limiar do filtro em metades do mês de calibração; os números dela ficam no histórico do git e na seção 4.1 de `docs/fases/fase-06b-modelo-v2.md`.
