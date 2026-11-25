# Relatório de decisão — modelos

## Hipóteses e fonte

- **fonte:** data.binance.vision, 1m, 2024-11 a 2026-10
- **modelo:** HistGradientBoosting (scikit-learn) + calibração isotônica, features fs-1
- **walk-forward:** treino 6 meses (1 a cada 3 minutos) → calibração 1 mês → teste 1 mês; purga pelo vencimento real e embargo de 1 h; holdout final de 3 meses
- **decisão:** COMPRA se p ≥ equilíbrio + 1 p.p.; VENDA se p ≤ 1 − (equilíbrio + 1 p.p.)
- **payout:** 0.86 (hipotético até o cliente informar o da Exnova)
- **preço:** 1m (entrada na abertura do minuto da decisão): limite superior otimista para 1m e 5m

## Resultado por ativo e expiração (fora da amostra)

| Ativo | Exp. | Operações | Taxa | Wilson inf. | Equilíbrio | Melhor simples | Meses acima | Holdout | ECE | Dobras | Recomendação | Motivo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BTCUSDT | 1m | 41981 | 55.42% | 54.95% | 53.76% | 50.57% | 78.57% | 56.21% | 0.74% | 14 | **ligar** | passou em todos os critérios |
| BTCUSDT | 5m | 9156 | 53.96% | 52.94% | 53.76% | 50.09% | 42.86% | 52.73% | 0.79% | 14 | **não ligar** | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| BTCUSDT | 15m | 6652 | 54.86% | 53.66% | 53.76% | 50.28% | 71.43% | 52.69% | 1.52% | 14 | **não ligar** | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| BTCUSDT | 30m | 4723 | 53.97% | 52.55% | 53.76% | 50.39% | 50.00% | 53.86% | 1.78% | 14 | **não ligar** | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| BTCUSDT | 60m | 2308 | 52.77% | 50.73% | 53.76% | 50.24% | 14.29% | 53.99% | 2.25% | 14 | **não ligar** | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| ETHUSDT | 1m | 33108 | 54.54% | 54.00% | 53.76% | 50.31% | 85.71% | 53.04% | 0.65% | 14 | **não ligar** | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| ETHUSDT | 5m | 26075 | 55.08% | 54.48% | 53.76% | 50.14% | 78.57% | 53.20% | 1.04% | 14 | **não ligar** | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| ETHUSDT | 15m | 17695 | 55.11% | 54.37% | 53.76% | 50.19% | 71.43% | 53.92% | 1.37% | 14 | **não ligar** | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| ETHUSDT | 30m | 10390 | 54.30% | 53.34% | 53.76% | 50.37% | 64.29% | 54.05% | 1.97% | 14 | **não ligar** | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| ETHUSDT | 60m | 5572 | 53.21% | 51.90% | 53.76% | 50.25% | 28.57% | 54.10% | 1.82% | 14 | **não ligar** | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |

## Conclusão

Combinações aprovadas: BTCUSDT 1m.

Execução: workflow "Modelos", run 45621323853, payout 0.86.
