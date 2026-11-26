# Fase 6b — Modelo v2 (rótulos de 1 s, microestrutura, filtro de apertados)

- **Status:** concluída. **Resultado: nenhuma combinação aprovada.** Todas continuam em AGUARDAR.
- **Plano:** `docs/superpowers/plans/2026-11-25-fase-06b-modelo-v2.md`
- **Relatório real:** `docs/laboratorio/2026-11-26-modelo-v2-payout-86.md` (workflow "Modelos v2", run 45647410250)

## 1. Objetivo

A Fase 6 mostrou que o modelo v1 passava no walk-forward com preços de 1 min, mas era reprovado quando a entrada era simulada de forma realista com preços de 1 s. A Fase 6b refaz o modelo já dentro da realidade de 1 s e tenta três melhorias: rótulos realistas, informação de microestrutura e um filtro que evita operações "apertadas".

## 2. O que foi construído

| Parte | Onde | O que faz |
|---|---|---|
| Leitura de 1 s | `modelos/dados_1s.py` | Lê o zip mensal da Binance direto, só com as colunas usadas, incluindo o número de negócios |
| Microestrutura | `features/microestrutura.py` | Resume os 60 segundos de cada minuto em 17 colunas `mic_*`: taxa de compra agressora no minuto e nos últimos 10 s e a variação entre as duas, retorno dos últimos 10 s e 30 s, volatilidade realizada (1 e 5 min, e relativa a 15 min), fração de segundos sem mudança, segundos desde a última mudança, explosão de volume nos últimos 10 s, sequência de segundos no mesmo sentido, negócios relativos, distância ao VWAP do minuto. Agrega mês a mês com o mesmo resultado da série inteira |
| `fs-2` | `features/fs2.py` | `fs-1` intacto + microestrutura + calendário (hora, minuto da hora, dia da semana) = 247 colunas |
| Rótulos de 1 s | `modelos/rotulos.py::rotular_1s` | Entrada num segundo sorteado entre a decisão + 2 s e o prazo de compra; vencimento alinhado ao relógio da Exnova; marca "apertado" |
| Filtro de apertados | `modelos/filtro.py` | Classificador que prevê "apertado". O limiar é escolhido só no mês de calibração |
| Walk-forward v2 | `modelos/avaliacao_v2.py` | O mesmo da Fase 6, mas com teste, holdout e estratégias simples simulados em 1 s com entrada sorteada |
| Relatório | `modelos/decisao_v2.py` e o workflow `modelos-v2.yml` | Usa os critérios da Fase 6 (`consolidar`) e acrescenta dois diagnósticos |

**Causalidade:** `tests/regressao_vazamento/test_causalidade_fs2.py` confere que a linha do minuto *t* é a mesma quando os segundos são cortados no fim de *t* e quando os segundos futuros são embaralhados. O teste foi **validado por mutação**: quatro vazamentos introduzidos de propósito fizeram o teste falhar. Foram eles: `.shift(-1)` numa janela, `bfill` no lugar de `ffill`, minuto deslocado 1 s para o futuro e preço de um segundo futuro.

## 3. Decisões fixadas antes de ver resultados

- **Período:** 24 meses (2024-11 a 2026-10), com 1 s em todos eles. Isso dá 63 milhões de segundos por ativo e o mesmo período e as mesmas 14 dobras da Fase 6. Com 6 a 9 meses não caberia nenhuma dobra, porque o esquema pede 6 + 1 + 1 + 3 = 11 meses. A rodada de fumaça (run 45646713348) mostrou cerca de 6 s por mês de 1 s. A rodada real levou **39 min**, com pico de **5,8 GB**, abaixo do limite de cerca de 7 GB.
- **Modelo:** HistGradientBoosting com os hiperparâmetros da Fase 6, sem busca. A direção é treinada só com amostras de treino não apertadas. A calibração isotônica usa todas as amostras do mês de calibração.
- **Filtro:** no mês de calibração, o sistema escolhe entre não filtrar e cortar os 10%, 25% ou 50% de sinais com maior chance de terminar apertados. Fica a opção com o maior limite inferior de Wilson.
- **Candidato à aprovação:** só `fs-2 + filtro`. A correção de Benjamini-Hochberg é feita sobre as 4 combinações. `fs-2 sem filtro` e `fs-1 + filtro` (com rótulos de 1 s) são só diagnósticos.
- **Payout de decisão:** 0,86, o que dá equilíbrio de 53,76% e exige Wilson inferior acima de 54,76%.

## 4. Resultado com dados reais (payout 0,86)

| Combinação | Taxa fora da amostra | Wilson inf. | Meses acima | Apertados | Holdout (taxa / Wilson inf. / apertados) | Recomendação |
|---|---|---|---|---|---|---|
| BTC 1m | 53,24% (6.598 operações) | 52,04% | 36% | 27,4% | 53,00% / 50,17% / 33,4% | não ligar |
| BTC 5m | 50,39% (2.296) | 48,35% | 21% | 15,6% | 50,94% / 49,04% / 24,1% | não ligar |
| ETH 1m | 53,83% (12.517) | 52,96% | 43% | 22,1% | 54,66% / 52,63% / 14,9% | não ligar |
| ETH 5m | 51,72% (9.134) | 50,69% | 29% | 11,6% | 52,37% / 50,74% / 8,5% | não ligar |

As estratégias simples, nas mesmas janelas e com 1 s, ficaram entre 50,07% e 50,34%. Nenhuma combinação cumpre o critério de Wilson, o de 70% dos meses acima do equilíbrio, o de Benjamini-Hochberg ou a confirmação no holdout.

### O que os diagnósticos mostram

1. **A maior parte da vantagem da Fase 6 vinha da entrada otimista de 1 min.** Com rótulos e entradas de 1 s, o modelo fica em 50 a 54%, contra 53 a 55,5% na Fase 6. Ele ainda supera as estratégias simples em 3 a 3,5 pontos percentuais (p.p.) no 1m e em 0,3 a 1,5 p.p. no 5m, mas não supera o custo do payout.
2. **A microestrutura não trouxe ganho consistente.** `fs-1 + filtro` e `fs-2 + filtro` ficaram praticamente iguais no 1m (BTC 53,23% contra 53,24%; ETH 53,49% contra 53,83%). No 5m, o `fs-2` ficou pior (BTC 50,39% contra 52,60%; ETH 51,72% contra 52,49%).
3. **O filtro faz o que promete nos apertados, mas isso não basta.** Ele reduz a fração de operações apertadas:

   | Combinação | Teste: sem filtro → com filtro | Holdout: sem filtro → com filtro |
   |---|---|---|
   | BTC 1m | 34,9% → 27,4% | 47,7% → 33,4% |
   | ETH 1m | 26,1% → 22,1% | 30,1% → 14,9% |

   Ele também melhora um pouco a taxa do ETH 1m (de 53,32% para 53,83%, e de 52,57% para 54,66% no holdout). Mesmo excluindo todas as operações apertadas, a taxa fica em 54,1 a 54,5% no 1m, ainda perto do equilíbrio.
4. **A calibração continua boa:** o erro de calibração (ECE) ficou entre 0,7% e 1,2%.

## 5. Limitações declaradas

- O holdout (2026-08 a 2026-10) é o mesmo da Fase 6 e já tinha sido visto uma vez pelo modelo v1. Ainda não existem meses completos novos; o primeiro será 2026-11, a partir de dezembro.
- A escolha do limiar do filtro usa o mesmo mês que a calibração isotônica. Ela não toca no teste nem no holdout, mas tem ruído de seleção.
- O corte de 5 min (100 s) continua sendo uma hipótese. O preço de referência é o da Binance, não o da Exnova.

## 6. Decisão técnica e próximos passos

**Nenhuma combinação está validada para vender sinais.** A plataforma continua mostrando AGUARDAR em todas. Pela regra do projeto, nada foi ajustado depois de ver o resultado.

Opções para o cliente:

1. Seguir com o caminho B, **painel de análise sem sinais**, enquanto a pesquisa continua.
2. Testar fontes de informação realmente novas, como livro de ofertas, fluxo entre corretoras e funding, e não só derivados dos klines. Avaliar com meses novos, a partir de 2026-11, como holdout limpo.
3. Investigar o preço de referência da própria Exnova. Em 1 min, 15 a 30% das operações filtradas ainda terminam apertadas, e ali a diferença entre a Binance e a Exnova decide o resultado.
