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

## 3. O que decide a viabilidade

O payout real da Exnova. O ponto de equilíbrio é 1/(1 + payout):

| Payout | Equilíbrio | Combinações acima do equilíbrio + 1 p.p. (pelo Wilson) |
|---|---|---|
| 85% | 54,05% | nenhuma |
| 88% | 53,19% | BTC 1m, ETH 5m, ETH 15m |
| 90% | 52,63% | BTC 1m, BTC 15m, ETH 1m, ETH 5m, ETH 15m |

A tabela é só uma referência: com outro payout, o relatório precisa ser gerado de novo (workflow "Modelos"), porque o limiar de decisão muda junto.

## 4. Próximo passo (decisão do cliente)

1. Informar o payout real da Exnova por expiração e rodar o workflow "Modelos" com ele.
2. Se alguma combinação for aprovada, seguir para a Fase 7 (motor de sinais ao vivo e 60 a 90 dias de teste ao vivo) só com ela.
3. Se nenhuma for aprovada, as alternativas são:
   - melhorar o modelo com mais features (por exemplo, livro de ofertas e funding), com dados de 1 s e com ajuste de hiperparâmetros em validação;
   - lançar o produto como painel de análise (caminho B), sem sinais.
