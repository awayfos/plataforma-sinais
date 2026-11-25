# Relatório de decisão — modelos

## Hipóteses e fonte

- **fonte:** data.binance.vision, 1m, 2024-11 a 2026-10
- **modelo:** HistGradientBoosting (scikit-learn) + calibração isotônica, features fs-1
- **walk-forward:** treino 6 meses (1 a cada 3 minutos) → calibração 1 mês → teste 1 mês; purga pelo vencimento real e embargo de 1 h; holdout final de 3 meses
- **decisão:** COMPRA se p ≥ equilíbrio + 1 p.p.; VENDA se p ≤ 1 − (equilíbrio + 1 p.p.)
- **payout:** 0.89 (hipotético até o cliente informar o da Exnova)
- **preço:** 1m (entrada na abertura do minuto da decisão): limite superior otimista para 1m e 5m

## Resultado por ativo e expiração (fora da amostra)

| Ativo | Exp. | Operações | Taxa | Wilson inf. | Equilíbrio | Melhor simples | Meses acima | Holdout | ECE | Dobras | Recomendação | Motivo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BTCUSDT | 1m | 61107 | 54.83% | 54.43% | 52.91% | 50.57% | 92.86% | 54.02% | 0.74% | 14 | **ligar** | passou em todos os critérios |
| BTCUSDT | 5m | 14131 | 53.54% | 52.72% | 52.91% | 50.09% | 64.29% | 52.73% | 0.79% | 14 | **não ligar** | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| BTCUSDT | 15m | 11843 | 53.68% | 52.78% | 52.91% | 50.47% | 64.29% | 52.69% | 1.52% | 14 | **não ligar** | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| BTCUSDT | 30m | 7190 | 52.70% | 51.54% | 52.91% | 50.58% | 57.14% | 54.31% | 1.78% | 14 | **não ligar** | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| BTCUSDT | 60m | 2815 | 53.53% | 51.69% | 52.91% | 50.52% | 42.86% | 53.99% | 2.25% | 14 | **não ligar** | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| ETHUSDT | 1m | 51348 | 54.16% | 53.73% | 52.91% | 50.22% | 92.86% | 52.63% | 0.65% | 14 | **não ligar** | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| ETHUSDT | 5m | 40864 | 54.46% | 53.98% | 52.91% | 50.17% | 85.71% | 52.84% | 1.04% | 14 | **não ligar** | holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| ETHUSDT | 15m | 23136 | 54.29% | 53.65% | 52.91% | 50.19% | 78.57% | 53.99% | 1.37% | 14 | **não ligar** | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| ETHUSDT | 30m | 13162 | 53.52% | 52.66% | 52.91% | 50.35% | 78.57% | 54.05% | 1.97% | 14 | **não ligar** | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |
| ETHUSDT | 60m | 6765 | 53.05% | 51.86% | 52.91% | 50.25% | 42.86% | 54.13% | 1.82% | 14 | **não ligar** | limite inferior de Wilson não supera o equilíbrio + 1 p.p.; menos de 70% dos meses testados acima do equilíbrio; não sobrevive à correção de Benjamini-Hochberg; holdout sem confirmação (mínimo 100 operações e Wilson inferior acima do equilíbrio) |

## Conclusão

Combinações aprovadas: BTCUSDT 1m.

Execução: workflow "Modelos", run 45621337727, payout 0.89.
