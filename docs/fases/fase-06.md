# Fase 6 — Modelos e calibração (relatório de decisão)

- **Status:** concluída. **Portão de decisão com o cliente.**
- **Plano:** `docs/superpowers/plans/2026-11-25-fase-06-modelos.md`
- **Relatório real:** `docs/laboratorio/2026-11-25-modelos.md`

## 1. O que foi construído

- Rótulos com as regras de vencimento da Exnova.
- Treino com HistGradientBoosting sobre as cerca de 227 features `fs-1` e calibração isotônica num mês separado.
- Walk-forward com 14 dobras: 6 meses de treino, 1 de calibração e 1 de teste, com purga pelo vencimento real.
- Holdout final de 3 meses, avaliado uma única vez.
- Registro de modelos com campeão/desafiante e teste de significância.
- Relatório de decisão com os critérios do design §13.3.

## 2. Resultado com dados reais (24 meses, BTC e ETH, payout hipotético de 85%)

| | Estratégias simples | Modelo (fora da amostra) |
|---|---|---|
| Taxa de acerto | 50,1% a 50,6% | **53,1% a 55,5%** |
| Mais perto de passar | — | BTC 1m: 55,49% (Wilson 54,99%, faltam 0,06 p.p. de margem); ETH 5m: 55,48% (86% dos meses acima) |

- O modelo supera as estratégias simples de forma consistente, em **3 a 5 pontos percentuais**, em todas as combinações. Há sinal real nos dados.
- Mesmo assim, **nenhuma combinação passou** no critério de margem sobre o equilíbrio de 54,05% com payout de 85%. Por isso, pela regra do produto, todas ficam em AGUARDAR.
- A calibração está boa: o erro de calibração ficou entre 0,7% e 2,3%. Quando o modelo diz 55%, a taxa real fica perto de 55%.
- As linhas de 1m e 5m usam entrada na abertura do minuto, um limite superior otimista. Em 1 min, 41% das operações do BTC terminam apertadas (Fase 5), então o 1m real deve ser pior que o mostrado.

## 3. Com o payout real informado pelo cliente (86% a 89%)

| Payout | Equilíbrio | Aprovada no walk-forward | Validação realista com 1 s (holdout) |
|---|---|---|---|
| 86% | 53,76% | BTC 1m (55,42%, Wilson 54,95%) | **reprovada**: 54,10%, Wilson 52,98%, 62% das operações apertadas |
| 89% | 52,91% | BTC 1m (54,83%) | não repetida: o caso de 86% já reprova o 1m na prática |

- Com a entrada realista (2 s depois do sinal até o prazo de compra, preço do segundo), a taxa do BTC 1m cai de 56,2% para **54,1%**. Isso continua acima do equilíbrio de 53,76%, mas sem significância: o limite de Wilson fica em 52,98%.
- **62% das operações de 1 min do holdout terminaram apertadas.** Qualquer diferença entre o preço da Binance e o da Exnova pode inverter esses resultados.
- ETH 5m e 15m ficaram perto (54,5% a 55,1% fora da amostra), mas não se confirmaram no holdout.

**Decisão técnica:** nenhuma combinação está validada para vender sinais hoje. Pela regra do produto, a plataforma mostra AGUARDAR em todas.

## 4. Próximo passo (decisão do cliente)

1. **Melhorar o modelo e repetir o teste** (recomendado antes de vender sinais):
   - treinar e validar 1m e 5m direto com dados de 1 s;
   - acrescentar informação de microestrutura (fluxo de agressão por segundo, livro de ofertas);
   - fazer seleção de features e ajuste em validação.
2. **Lançar como painel de análise** (caminho B), sem sinais, enquanto o modelo amadurece.
3. **As duas coisas em paralelo:** construir a plataforma web (Fases 8 a 10) com o painel de análise e ativar sinais só quando um modelo passar na validação.
