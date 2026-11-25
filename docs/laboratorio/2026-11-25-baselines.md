# Relatório do laboratório

## Hipóteses e fonte

- **fonte:** data.binance.vision, klines de 1m, (2024, 11) a (2026, 10)
- **payout:** 0.85 (hipotético até o cliente informar o da Exnova)
- **preço:** 1m: entrada = abertura do minuto da decisão; vencimento = preço na fronteira
- **latência:** 2 s (checada contra o prazo de compra)
- **cortes 5m/30m/1h:** hipóteses (1/3 da grade) até confirmar na Exnova
- **lacunas:** nenhuma

## Resultados

| Ativo | Expiração | Estratégia | Operações | Taxa | Wilson inf. | Equilíbrio | Valor esperado | Meses acima | Aprovada |
|---|---|---|---|---|---|---|---|---|---|
| BTCUSDT | 1m | sempre_compra | 1051199 | 50.06% | 49.96% | 54.05% | -0.0714 | 0.00% | não |
| BTCUSDT | 1m | sempre_venda | 1051199 | 49.94% | 49.84% | 54.05% | -0.0735 | 0.00% | não |
| BTCUSDT | 1m | seguir_ultimo | 1016660 | 50.81% | 50.71% | 54.05% | -0.0582 | 0.00% | não |
| BTCUSDT | 1m | aleatoria | 1051199 | 49.93% | 49.84% | 54.05% | -0.0737 | 0.00% | não |
| BTCUSDT | 5m | sempre_compra | 210240 | 49.94% | 49.72% | 54.05% | -0.0760 | 0.00% | não |
| BTCUSDT | 5m | sempre_venda | 210240 | 50.06% | 49.85% | 54.05% | -0.0736 | 0.00% | não |
| BTCUSDT | 5m | seguir_ultimo | 210154 | 49.60% | 49.38% | 54.05% | -0.0822 | 0.00% | não |
| BTCUSDT | 5m | aleatoria | 210240 | 49.95% | 49.74% | 54.05% | -0.0756 | 0.00% | não |
| BTCUSDT | 15m | sempre_compra | 70080 | 49.86% | 49.49% | 54.05% | -0.0775 | 0.00% | não |
| BTCUSDT | 15m | sempre_venda | 70080 | 50.14% | 49.77% | 54.05% | -0.0724 | 0.00% | não |
| BTCUSDT | 15m | seguir_ultimo | 70080 | 49.73% | 49.36% | 54.05% | -0.0800 | 0.00% | não |
| BTCUSDT | 15m | aleatoria | 70080 | 50.16% | 49.79% | 54.05% | -0.0720 | 0.00% | não |
| BTCUSDT | 30m | sempre_compra | 35040 | 50.66% | 50.14% | 54.05% | -0.0628 | 0.00% | não |
| BTCUSDT | 30m | sempre_venda | 35040 | 49.34% | 48.82% | 54.05% | -0.0872 | 0.00% | não |
| BTCUSDT | 30m | seguir_ultimo | 35040 | 50.16% | 49.64% | 54.05% | -0.0720 | 0.00% | não |
| BTCUSDT | 30m | aleatoria | 35040 | 50.33% | 49.81% | 54.05% | -0.0688 | 0.00% | não |
| BTCUSDT | 60m | sempre_compra | 17520 | 50.34% | 49.60% | 54.05% | -0.0688 | 4.00% | não |
| BTCUSDT | 60m | sempre_venda | 17520 | 49.66% | 48.92% | 54.05% | -0.0812 | 0.00% | não |
| BTCUSDT | 60m | seguir_ultimo | 17520 | 49.67% | 48.93% | 54.05% | -0.0810 | 0.00% | não |
| BTCUSDT | 60m | aleatoria | 17520 | 50.05% | 49.31% | 54.05% | -0.0740 | 0.00% | não |
| ETHUSDT | 1m | sempre_compra | 1051199 | 50.23% | 50.14% | 54.05% | -0.0698 | 0.00% | não |
| ETHUSDT | 1m | sempre_venda | 1051199 | 49.77% | 49.67% | 54.05% | -0.0783 | 0.00% | não |
| ETHUSDT | 1m | seguir_ultimo | 1038159 | 49.65% | 49.55% | 54.05% | -0.0805 | 0.00% | não |
| ETHUSDT | 1m | aleatoria | 1051199 | 49.95% | 49.86% | 54.05% | -0.0749 | 0.00% | não |
| ETHUSDT | 5m | sempre_compra | 210240 | 50.16% | 49.94% | 54.05% | -0.0720 | 0.00% | não |
| ETHUSDT | 5m | sempre_venda | 210240 | 49.84% | 49.63% | 54.05% | -0.0777 | 0.00% | não |
| ETHUSDT | 5m | seguir_ultimo | 210226 | 49.36% | 49.15% | 54.05% | -0.0866 | 0.00% | não |
| ETHUSDT | 5m | aleatoria | 210240 | 50.06% | 49.85% | 54.05% | -0.0737 | 0.00% | não |
| ETHUSDT | 15m | sempre_compra | 70080 | 50.38% | 50.01% | 54.05% | -0.0678 | 0.00% | não |
| ETHUSDT | 15m | sempre_venda | 70080 | 49.62% | 49.25% | 54.05% | -0.0820 | 0.00% | não |
| ETHUSDT | 15m | seguir_ultimo | 70080 | 49.90% | 49.53% | 54.05% | -0.0767 | 0.00% | não |
| ETHUSDT | 15m | aleatoria | 70080 | 50.21% | 49.84% | 54.05% | -0.0711 | 0.00% | não |
| ETHUSDT | 30m | sempre_compra | 35040 | 50.57% | 50.05% | 54.05% | -0.0644 | 0.00% | não |
| ETHUSDT | 30m | sempre_venda | 35040 | 49.43% | 48.91% | 54.05% | -0.0855 | 0.00% | não |
| ETHUSDT | 30m | seguir_ultimo | 35040 | 49.62% | 49.10% | 54.05% | -0.0820 | 0.00% | não |
| ETHUSDT | 30m | aleatoria | 35040 | 50.41% | 49.88% | 54.05% | -0.0674 | 4.00% | não |
| ETHUSDT | 60m | sempre_compra | 17520 | 50.57% | 49.83% | 54.05% | -0.0644 | 4.00% | não |
| ETHUSDT | 60m | sempre_venda | 17520 | 49.43% | 48.69% | 54.05% | -0.0856 | 0.00% | não |
| ETHUSDT | 60m | seguir_ultimo | 17520 | 49.49% | 48.75% | 54.05% | -0.0844 | 0.00% | não |
| ETHUSDT | 60m | aleatoria | 17520 | 49.99% | 49.25% | 54.05% | -0.0751 | 0.00% | não |

Aprovação: Benjamini-Hochberg (q = 5%) sobre todas as linhas, pelo menos 300 operações decididas, limite inferior de Wilson acima do equilíbrio + 1 p.p. e pelo menos 70% dos meses acima do equilíbrio.

Execução: GitHub Actions, workflow "Laboratório", run 45554795945 (2026-11-25).
