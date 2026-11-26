# Relatório de decisão — modelo v2 (Fase 6b)

## Hipóteses e fonte

- **fonte:** data.binance.vision, klines de 1m e 1s, 2024-11 a 2026-10 (24 meses; segundos por ativo: {'BTCUSDT': 63072000, 'ETHUSDT': 63072000})
- **modelo:** HistGradientBoosting (hiperparâmetros da Fase 6, sem busca) + calibração isotônica; features fs-2 = fs-1 + 17 de microestrutura de 1 s + 3 de calendário
- **rótulo:** entrada num segundo sorteado entre decisão + 2 s e o prazo de compra; vencimento alinhado ao relógio da Exnova; preço = fechamento do candle de 1 s
- **treino da direção:** só amostras de treino não apertadas; calibração com todas
- **filtro de apertados:** HGB prevê apertado (|Δ| ≤ 0,01%); limiar escolhido no mês de calibração entre sem filtro e cortar os 10%/25%/50% mais prováveis (maior Wilson inf.)
- **walk-forward:** treino 6 meses (1 a cada 3 minutos) → calibração 1 mês → teste 1 mês; purga pelo vencimento real e embargo de 1 h; holdout final de 3 meses avaliado uma vez
- **simulação:** teste, holdout e estratégias simples com 1 s e entrada sorteada (semente 7); um sinal ativo por vez
- **decisão:** COMPRA se p ≥ equilíbrio + 1 p.p.; VENDA se p ≤ 1 − (equilíbrio + 1 p.p.)
- **payout:** 0.86 (caso de decisão: menor payout informado da Exnova)
- **cortes:** 1m: 30 s (confirmado); 5m: 100 s (hipótese de 1/3 da grade)
- **lacunas:** nenhuma

## Resultado do candidato (fs-2 + filtro de apertados)

| Ativo | Exp. | Operações | Taxa | Wilson inf. | Equilíbrio | Melhor simples | Meses acima | Apertados | Taxa s/ apertados | Holdout: operações | Holdout: taxa | Holdout: Wilson inf. | Holdout: apertados | ECE | Dobras | Recomendação | Motivo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BTCUSDT | 1m | 6598 | 53.24% | 52.04% | 53.76% | 50.25% | 35.71% | 27.37% | 54.09% | 1202 | 53.00% | 50.17% | 33.41% | 0.72% | 14 | **não ligar** | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| BTCUSDT | 5m | 2296 | 50.39% | 48.35% | 53.76% | 50.07% | 21.43% | 15.63% | 51.94% | 2672 | 50.94% | 49.04% | 24.10% | 0.76% | 14 | **não ligar** | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| ETHUSDT | 1m | 12517 | 53.83% | 52.96% | 53.76% | 50.34% | 42.86% | 22.13% | 54.52% | 2327 | 54.66% | 52.63% | 14.90% | 0.74% | 14 | **não ligar** | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| ETHUSDT | 5m | 9134 | 51.72% | 50.69% | 53.76% | 50.21% | 28.57% | 11.64% | 51.91% | 3605 | 52.37% | 50.74% | 8.46% | 1.18% | 14 | **não ligar** | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |

Apertados: fração das operações liquidadas com |Δ preço| ≤ 0,01%. Fora da amostra = dobras do walk-forward agregadas; holdout = últimos 3 meses, avaliados uma vez.

## Filtro de apertados (escolhido só na calibração)

| Ativo | Exp. | Períodos com filtro | Fração média de sinais cortada | Limiares |
|---|---|---|---|---|
| BTCUSDT | 1m | 5 de 15 | 13.13% | —, —, —, —, —, —, 0.211, —, —, —, —, 0.386, 0.626, 0.322, 0.591 |
| BTCUSDT | 5m | 6 de 15 | 9.10% | 0.199, 0.328, —, —, —, —, —, 0.329, 0.167, 0.091, —, —, 0.334, —, — |
| ETHUSDT | 1m | 8 de 15 | 20.62% | 0.134, —, 0.216, —, —, 0.222, 0.189, 0.295, 0.237, —, —, —, 0.299, —, 0.232 |
| ETHUSDT | 5m | 7 de 15 | 18.65% | 0.072, —, 0.142, —, —, 0.114, —, —, —, 0.068, 0.088, —, 0.195, —, 0.121 |

## Diagnóstico: fs-2 sem filtro (sem direito a aprovação)

Mesmo walk-forward e mesmas janelas; serve só para entender o efeito de cada parte.

| Ativo | Exp. | Operações | Taxa | Wilson inf. | Equilíbrio | Melhor simples | Meses acima | Apertados | Taxa s/ apertados | Holdout: operações | Holdout: taxa | Holdout: Wilson inf. | Holdout: apertados | ECE | Dobras | Recomendação | Motivo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BTCUSDT | 1m | 8636 | 53.21% | 52.15% | 53.76% | 50.25% | 28.57% | 34.93% | 54.09% | 1704 | 52.23% | 49.86% | 47.74% | 0.72% | 14 | (teria: não ligar) | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| BTCUSDT | 5m | 2621 | 51.55% | 49.63% | 53.76% | 50.07% | 14.29% | 17.52% | 52.60% | 2672 | 50.94% | 49.04% | 24.10% | 0.76% | 14 | (teria: não ligar) | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| ETHUSDT | 1m | 15517 | 53.32% | 52.53% | 53.76% | 50.34% | 28.57% | 26.11% | 54.07% | 5020 | 52.57% | 51.19% | 30.12% | 0.74% | 14 | (teria: não ligar) | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| ETHUSDT | 5m | 10620 | 52.16% | 51.21% | 53.76% | 50.21% | 35.71% | 11.74% | 52.54% | 7802 | 51.96% | 50.85% | 15.94% | 1.18% | 14 | (teria: não ligar) | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |

## Diagnóstico: fs-1 + filtro, rótulos de 1 s (sem direito a aprovação)

Mesmo walk-forward e mesmas janelas; serve só para entender o efeito de cada parte.

| Ativo | Exp. | Operações | Taxa | Wilson inf. | Equilíbrio | Melhor simples | Meses acima | Apertados | Taxa s/ apertados | Holdout: operações | Holdout: taxa | Holdout: Wilson inf. | Holdout: apertados | ECE | Dobras | Recomendação | Motivo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BTCUSDT | 1m | 5395 | 53.23% | 51.90% | 53.76% | 50.72% | 35.71% | 36.34% | 54.06% | 499 | 52.10% | 47.72% | 18.36% | 0.65% | 14 | (teria: não ligar) | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| BTCUSDT | 5m | 2131 | 52.60% | 50.48% | 53.76% | 50.84% | 35.71% | 16.24% | 53.11% | 1130 | 51.15% | 48.24% | 24.33% | 0.74% | 14 | (teria: não ligar) | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| ETHUSDT | 1m | 9145 | 53.49% | 52.47% | 53.76% | 50.24% | 50.00% | 15.24% | 54.23% | 2023 | 55.22% | 53.04% | 27.75% | 0.68% | 14 | (teria: não ligar) | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| ETHUSDT | 5m | 9166 | 52.49% | 51.46% | 53.76% | 50.21% | 35.71% | 12.14% | 52.74% | 3114 | 51.83% | 50.07% | 8.62% | 1.16% | 14 | (teria: não ligar) | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |

## Conclusão

Nenhuma combinação passou nos critérios. Pela regra do produto, todas mostram AGUARDAR até que um modelo seja aprovado.

Tempo total: 39.4 min; pico de memória 5831 MB.

Execução: workflow "Modelos v2", run 45647410250 (commit 9c28b3a), `--meses 24 --fim 2026-10 --payout 0.86`; 39 min, pico de memória 5,8 GB (`/usr/bin/time -v`: 5.971.064 kB). Relatório copiado do log do job.
