# Fase 5 — Backtesting e validação

- **Status:** concluída e incorporada à `main`
- **Plano:** `docs/superpowers/plans/2026-11-25-fase-05-backtesting.md`
- **Relatório real:** `docs/laboratorio/2026-11-25-baselines.md`

## 1. Objetivo

Simular sinais com as regras reais da Exnova, medir o resultado com estatística honesta e rodar a primeira avaliação com dados reais.

## 2. Entregue

| Módulo | Conteúdo |
|---|---|
| `corretoras.regras` | Vencimento alinhado ao relógio com prazo de compra (1 min e 15 min confirmados; 5 min, 30 min e 1 h como hipóteses), liquidação com empate devolvido, ponto de equilíbrio do payout |
| `backtest.precos` | Preço de referência em 1 s (exato) ou 1 min (só nas fronteiras de minuto) |
| `backtest.simulador` | Operações com latência, prazo de compra e um sinal ativo por vez |
| `backtest.metricas` | Taxa sem empates, Wilson 95%, valor esperado, p-valor binomial exato, Benjamini-Hochberg, métricas por grupo |
| `backtest.baselines` | Sempre compra, sempre venda, seguir o último candle, aleatória |
| `backtest.walk_forward` | Dobras mensais (treino → calibração → teste) e purga com embargo |
| `backtest.laboratorio` + workflow "Laboratório" | Baixa o histórico oficial e gera o relatório com as hipóteses declaradas |

## 3. Primeiro resultado com dados reais (24 meses, BTC e ETH, 1m)

Todas as estratégias simples ficaram entre **49,3% e 50,8%** de acerto em todas as expirações. O ponto de equilíbrio com payout de 85% é **54,05%**. O valor esperado ficou entre **−5,8% e −8,7% por operação**, e nenhuma combinação foi aprovada.

O resultado era esperado e mostra que o laboratório funciona. Sem análise, operar opções binárias perde, em média, cerca de 7% do valor de cada operação, que é a vantagem embutida no payout. Qualquer modelo da Fase 6 precisa superar esse patamar com margem e de forma estável.

## 4. Auditoria e limitações

- Com dados de 1 minuto, o preço de entrada é a abertura do minuto da decisão. Isso é otimista, porque o usuário real entra alguns segundos depois. Para expirações curtas, a validação final deve usar dados de 1 s.
- Payout de 0,85 e os cortes de 5 min, 30 min e 1 h são hipóteses. Os valores reais da Exnova mudam o ponto de equilíbrio.
- O walk-forward está pronto e será usado quando houver modelo para treinar (Fase 6).
