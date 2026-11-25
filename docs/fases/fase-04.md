# Fase 4 — Motores de análise

- **Status:** concluída e incorporada à `main` (revisão final feita, 6 pontos importantes corrigidos)
- **Plano:** `docs/superpowers/plans/2026-11-25-fase-04-motores-analise.md`

## 1. Objetivo

Criar uma biblioteca única e causal de análise técnica e o snapshot de features usado pela inteligência, com a garantia automática de que nenhuma análise usa dados futuros.

## 2. Entregue

| Módulo | Conteúdo |
|---|---|
| `analise.indicadores` | SMA, EMA, RMA (Wilder), RSI, MACD, Bollinger, ATR, ADX/DI, Estocástico, Ichimoku (o chikou fica só para o gráfico) |
| `analise.padroes_candle` | Doji, martelo, estrela cadente, pin bar, engolfo, marubozu, inside/outside bar, estrela da manhã/tarde, sequência e força (corpo relativo, pressão compradora) |
| `analise.estrutura` | Pivôs confirmados, HH/HL/LH/LL, tendência estrutural, BOS e CHoCH |
| `analise.volume` | Volume relativo, expansão/contração, pressão agressora acumulada, divergência, VWAP diário |
| `analise.regioes` | Suporte e resistência por agrupamento de pivôs: distância em ATR, número de toques (dificuldade de rompimento), rompimento e falso rompimento |
| `analise.fibonacci` | Níveis de retração e posição no último movimento |
| `analise.price_action` | Inclinação, impulso, desaceleração, lateralização, rejeição, correção e continuidade |
| `features.snapshot` | Conjunto `fs-1` (cerca de 60 features por tempo gráfico) com contexto de 5m, 15m e 1h, usando sempre o último candle maior já fechado |

## 3. Testes

- 191 testes passando localmente: valores conferidos à mão (RSI de Wilder, EMA semeada, Bollinger populacional, true range com gap), padrões construídos candle a candle e estruturas em zigue-zague.
- **Regressão de vazamento:** em 20 instantes sorteados de 3.000 minutos sintéticos, a linha `t` é idêntica com os dados cortados em `t` e com o futuro embaralhado. Validada por mutação: uma coluna que usa o futuro foi detectada em todos os tempos gráficos.

## 4. Auditoria

- Todos os dados de teste são sintéticos (passeio aleatório com semente fixa) e marcados como tal.
- Desempenho: o snapshot de 3.000 minutos leva menos de 1 s. Depois da revisão: 30 mil minutos em 2,0 s (antes 6,4 s); 2 anos de 1m estimados em cerca de 70 s por ativo. O cálculo ao vivo usa os últimos 18.000 minutos (`JANELA_AO_VIVO_1M`), e um teste garante que o resultado bate com o histórico completo.
