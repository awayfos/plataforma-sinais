# Fase 6b — Modelo v2 (rótulos de 1 s, microestrutura, filtro de apertados)

- **Status:** concluída. **Resultado: nenhuma combinação aprovada.** Todas continuam em AGUARDAR.
- **Plano:** `docs/superpowers/plans/2026-11-25-fase-06b-modelo-v2.md`
- **Relatório real:** `docs/laboratorio/2026-11-26-modelo-v2-payout-86.md` (workflow "Modelos v2", run 45760895573, rodada "principal")
- **Diagnóstico de sensibilidade (sem direito a aprovação):** `docs/laboratorio/2026-11-26-modelo-v2-sensibilidade-diagnostico.md` (mesmo run, rodada "sensibilidade")

## 1. Objetivo

A Fase 6 mostrou que o modelo v1 passava no walk-forward com preços de 1 min, mas era reprovado quando a entrada era simulada de forma realista com preços de 1 s. A Fase 6b refaz o modelo já dentro da realidade de 1 s e tenta três melhorias: rótulos realistas, informação de microestrutura e um filtro que evita operações "apertadas".

## 2. O que foi construído

| Parte | Onde | O que faz |
|---|---|---|
| Leitura de 1 s | `modelos/dados_1s.py` | Lê o zip mensal da Binance direto, só com as colunas usadas, incluindo o número de negócios |
| Microestrutura | `features/microestrutura.py` | Resume os 60 segundos de cada minuto em 17 colunas `mic_*`: taxa de compra agressora no minuto e nos últimos 10 s e a variação entre as duas, retorno dos últimos 10 s e 30 s, volatilidade realizada (1 e 5 min, e relativa a 15 min), fração de segundos sem mudança, segundos desde a última mudança, explosão de volume nos últimos 10 s, sequência de segundos no mesmo sentido, negócios relativos, distância ao VWAP do minuto. Agrega mês a mês com o mesmo resultado da série inteira |
| `fs-2` | `features/fs2.py` | `fs-1` intacto + microestrutura + calendário (hora, minuto da hora, dia da semana) = 247 colunas |
| Rótulos de 1 s | `modelos/rotulos.py::rotular_1s` | Entrada num segundo sorteado entre a decisão + 2 s e o prazo de compra; vencimento alinhado ao relógio da Exnova; marca "apertado" |
| Filtro de apertados | `modelos/filtro.py` | Classificador que prevê "apertado". O limiar é escolhido só na calibração |
| Walk-forward v2 | `modelos/avaliacao_v2.py` | O mesmo da Fase 6, mas com teste, holdout e estratégias simples simulados em 1 s com entrada sorteada. O mês de calibração é dividido em duas metades purgadas: a calibração isotônica usa a 1ª e o limiar do filtro, a 2ª |
| Execução opcional | `backtest/simulador.py` e `rotular_1s` | Entrada limitada (`entrada_max_ms`) e tolerância de preço de k × ATR (design §12.6). Desligadas por padrão |
| Relatório | `modelos/decisao_v2.py` e o workflow `modelos-v2.yml` | Usa os critérios da Fase 6 (`consolidar`), acrescenta dois diagnósticos e tem um modo de diagnóstico de sensibilidade em que nada é aprovado |

**Causalidade:** `tests/regressao_vazamento/test_causalidade_fs2.py` confere que a linha do minuto *t* é a mesma quando os segundos são cortados no fim de *t* e quando os segundos futuros são embaralhados. O teste foi **validado por mutação**: quatro vazamentos introduzidos de propósito fizeram o teste falhar. Foram eles: `.shift(-1)` numa janela, `bfill` no lugar de `ffill`, minuto deslocado 1 s para o futuro e preço de um segundo futuro.

**Prova contra falso negativo:** `tests/unit/modelos/test_ponta_a_ponta_fs2.py` planta um sinal só na microestrutura e o passa pelo caminho de produção inteiro: zip de 1 s → `ler_zip_1s` → `AgregadorMicro` → `montar_snapshot_em_blocos` → `combinar_fs2` → `avaliar_combinacao_v2`. O modelo encontra o sinal (taxa acima de 90%). Quando a janela dos últimos 10 s é esvaziada de propósito, o teste falha.

## 3. Decisões fixadas antes de ver resultados

- **Período:** 24 meses (2024-11 a 2026-10), com 1 s em todos eles. Isso dá 63 milhões de segundos por ativo e o mesmo período e as mesmas 14 dobras da Fase 6. Com 6 a 9 meses não caberia nenhuma dobra, porque o esquema pede 6 + 1 + 1 + 3 = 11 meses.
- **Tempo e memória:** a rodada de fumaça (run 45646713348) mostrou cerca de 6 s por mês de 1 s. A rodada principal com os dois diagnósticos levou **59 min**, com pico de **6,8 GB**, perto do limite de cerca de 7 GB do runner.
- **Modelo:** HistGradientBoosting com os hiperparâmetros da Fase 6, sem busca. A direção é treinada só com amostras de treino não apertadas.
- **Calibração e filtro:** o mês de calibração é dividido em duas metades. Cada metade é purgada pelo vencimento real, com embargo de 1 h. A calibração isotônica usa a 1ª metade. Na 2ª, o sistema escolhe entre não filtrar e cortar os 10%, 25% ou 50% de sinais com maior chance de terminar apertados, e fica a opção com o maior limite inferior de Wilson. Assim, o limiar não é escolhido sobre as mesmas amostras em que a isotônica foi ajustada.
- **Candidato à aprovação:** só `fs-2 + filtro`. A correção de Benjamini-Hochberg é feita sobre as 4 combinações. `fs-2 sem filtro` e `fs-1 + filtro` (com rótulos de 1 s) são só diagnósticos. Cada diagnóstico tem as próprias estratégias simples, com a aleatória na frequência dele.
- **Payout de decisão:** 0,86, o que dá equilíbrio de 53,76% e exige Wilson inferior acima de 54,76%.

## 4. Resultado com dados reais (payout 0,86)

| Combinação | Taxa fora da amostra | Wilson inf. | Meses acima | Apertados | Holdout (taxa / Wilson inf. / apertados) | Recomendação |
|---|---|---|---|---|---|---|
| BTC 1m | 53,74% (7.132 operações) | 52,58% | 43% | 28,3% | 52,33% / 50,84% / 46,5% | não ligar |
| BTC 5m | 52,53% (5.239) | 51,18% | 57% | 14,8% | 49,74% / 48,06% / 23,9% | não ligar |
| ETH 1m | 52,97% (10.607) | 52,01% | 29% | 17,4% | 53,87% / 51,93% / 15,1% | não ligar |
| ETH 5m | 51,45% (12.843) | 50,59% | 29% | 12,5% | 51,88% / 50,90% / 15,4% | não ligar |

As estratégias simples, nas mesmas janelas e com 1 s, ficaram entre 50,07% e 50,51%. Nenhuma combinação cumpre o critério de Wilson, o de 70% dos meses acima do equilíbrio, o de Benjamini-Hochberg ou a confirmação no holdout.

### 4.1 Primeira rodada, antes da correção da calibração

A primeira rodada (run 45647410250) escolhia o limiar do filtro no mesmo mês da calibração isotônica. Também não aprovou nada:

| Combinação | Taxa | Wilson inf. |
|---|---|---|
| BTC 1m | 53,24% | 52,04% |
| BTC 5m | 50,39% | 48,35% |
| ETH 1m | 53,83% | 52,96% |
| ETH 5m | 51,72% | 50,69% |

A diferença entre as duas rodadas, de até cerca de 2 p.p. por combinação, dá a medida do ruído de seleção do filtro.

### O que os diagnósticos mostram

1. **A maior parte da vantagem da Fase 6 vinha da entrada otimista de 1 min.** Com rótulos e entradas de 1 s, o modelo fica em 51,5 a 54%, contra 53 a 55,5% na Fase 6. Ele ainda supera as estratégias simples em 2,5 a 3,5 pontos percentuais (p.p.) no 1m e em 1,2 a 2,5 p.p. no 5m, mas não supera o custo do payout.
2. **A microestrutura não trouxe ganho consistente.** Comparação entre `fs-2 + filtro` e `fs-1 + filtro`:

   | Combinação | `fs-2 + filtro` | `fs-1 + filtro` |
   |---|---|---|
   | BTC 1m | 53,74% | 52,20% |
   | BTC 5m | 52,53% | 51,01% |
   | ETH 1m | 52,97% | 53,08% |
   | ETH 5m | 51,45% | 52,22% |

   O `fs-2` ganha cerca de 1,5 p.p. no BTC e perde até 0,8 p.p. no ETH. Nas duas rodadas, as diferenças ficaram dentro do ruído.
3. **O filtro reduz os apertados no teste, mas isso não basta.** Fração de operações apertadas no teste, sem filtro e com filtro:

   | Combinação | Sem filtro | Com filtro |
   |---|---|---|
   | BTC 1m | 36,2% | 28,3% |
   | ETH 1m | 22,9% | 17,4% |
   | BTC 5m | 17,1% | 14,8% |

   Mesmo assim, a taxa sobe só 0,5 a 0,8 p.p. no BTC. No ETH, sobe 0,3 p.p. no 1m e cai 0,5 p.p. no 5m. No holdout, a escolha da calibração foi não filtrar em 3 das 4 combinações. No ETH 1m, o filtro cortou 52% dos sinais, os apertados caíram de 31,2% para 15,1% e a taxa subiu de 52,57% para 53,87%. Mesmo excluindo todas as operações apertadas, a taxa fica abaixo de 54% em todas as combinações.
4. **A calibração continua boa:** o erro de calibração (ECE) ficou entre 0,9% e 1,5%.

## 5. Limitações declaradas

- O holdout (2026-08 a 2026-10) é o mesmo da Fase 6 e já tinha sido visto uma vez pelo modelo v1. Depois, foi visto de novo pela primeira rodada da v2. Ainda não existem meses completos novos; o primeiro será 2026-11, a partir de dezembro. Por isso, a rodada confirmatória da seção 7 usa só meses novos.
- O corte de 5 min (100 s) continua sendo uma hipótese. O preço de referência é o da Binance, não o da Exnova.

## 6. Decisão técnica e próximos passos

**Nenhuma combinação está validada para vender sinais.** A plataforma continua mostrando AGUARDAR em todas. Pela regra do projeto, nada foi ajustado para passar. As mudanças entre as rodadas vieram da revisão independente: correção metodológica da calibração e diagnóstico pré-registrado.

Opções para o cliente:

1. Seguir com o caminho B, **painel de análise sem sinais**, enquanto a pesquisa continua.
2. Rodar a confirmatória pré-registrada (seção 7) quando o mês 2027-01 for publicado. É a única rodada que pode ligar uma combinação na configuração de entrada limitada.
3. Testar fontes de informação realmente novas, como livro de ofertas, fluxo entre corretoras e funding, e não só derivados dos klines.
4. Investigar o preço de referência da própria Exnova. No 1m, 15 a 46% das operações ainda terminam apertadas, e ali a diferença entre a Binance e a Exnova decide o resultado.

## 7. Pré-registro da rodada confirmatória (fixado em 2026-11-26, antes do diagnóstico)

A revisão independente apontou que a entrada sorteada em toda a janela de compra é pessimista para o 5m. Na janela de 5 min, a entrada pode cair até cerca de 4 min depois do sinal. A revisão também apontou que essa entrada ignora a tolerância de preço do design §12.6. Por isso fica registrada **agora**, antes de qualquer número, a única configuração que será avaliada na rodada confirmatória com meses novos. Nada nela pode mudar depois do diagnóstico da seção 8.

| Item | Valor fixado |
|---|---|
| Código | O deste PR: `fs-2 + filtro`, com calibração isotônica na 1ª metade do mês de calibração e limiar do filtro na 2ª |
| Entrada | Segundo sorteado entre a decisão + 2 s e a decisão + 10 s (sem passar do prazo de compra), nos rótulos e na simulação |
| Tolerância de preço | Não entra se, na entrada, o preço estiver a mais de 0,5 × ATR(14) de 1m do preço da decisão (`FORA_DA_TOLERANCIA`). Vale para o modelo e para as estratégias simples |
| Dados | `--meses 27 --fim 2027-01`: holdout = 2026-11, 2026-12 e 2027-01, meses ainda não vistos por nenhum modelo |
| Walk-forward | Treino 6 meses (1 a cada 3 minutos), calibração 1, teste 1; purga pelo vencimento real; embargo de 1 h |
| Combinações | BTCUSDT e ETHUSDT × 1m e 5m; Benjamini-Hochberg sobre as 4 |
| Critérios | Os mesmos da Fase 6 (§13.3): n ≥ 300; Wilson inferior > equilíbrio + 1 p.p.; supera as estratégias simples; ≥ 70% dos meses testados acima do equilíbrio; Benjamini-Hochberg; holdout com ≥ 100 operações e Wilson inferior > equilíbrio |
| Payout | 0,86 (equilíbrio de 53,76%) |
| Execução | Workflow "Modelos v2" com `--meses 27 --fim 2027-01 --payout 0.86 --entrada-max-s 10 --tolerancia-atr 0.5`, depois da publicação do mês 2027-01 na Binance (a partir de 2027-02-01) |

**Implicação de produto, se aprovada:** o cartão do sinal precisa orientar a entrada nos primeiros 10 s e mostrar "Fora da janela, não entre" quando o preço se afastar mais que a tolerância.

Se qualquer item mudar, a rodada deixa de ser confirmatória e precisa de outros meses novos.

**Nota operacional (acrescentada depois do diagnóstico, sem mudar a configuração avaliada):** a rodada principal com os dois diagnósticos chegou a 6,8 GB de pico. Com 27 meses, a confirmatória deve rodar com `--sem-ablacao-fs1`. Essa opção só desliga o diagnóstico `fs-1` e não muda o candidato. A rodada de sensibilidade, com essa opção e 24 meses, ficou em 5,9 GB.

**Emenda A (2026-11-26, antes de existir qualquer dado dos meses novos):** a rodada confirmatória ganha uma **segunda família**, separada e declarada: BTCUSDT e ETHUSDT × **15m e 30m**, com exatamente a mesma configuração da tabela acima (código, entrada + 2..+10 s, tolerância de 0,5 × ATR, walk-forward, critérios, payout 0,86) e Benjamini-Hochberg sobre essas 4 combinações. Motivo: 15m é a expiração preferida do cliente e, na Fase 6 (entrada no preço de 1m), o ETH 15m chegou a 55,11% (Wilson inferior 54,37%) e o BTC 15m a 54,86%, sem passar; nenhuma rodada com 1 s e entrada rápida foi feita nessas expirações, então nenhum número desta configuração foi visto. A família 1m/5m acima não muda. Pendência de código antes da execução: opção de CLI para escolher as expirações avaliadas (hoje fixas em 1m e 5m), sem alterar nada do candidato.

## 8. Diagnóstico de sensibilidade (sem direito a aprovação)

Rodada "sensibilidade" do run 45760895573: a configuração pré-registrada na seção 7 (entrada entre a decisão + 2 s e + 10 s, tolerância de 0,5 × ATR) sobre os mesmos 24 meses. **Ela não aprova nada.** Esses meses e o holdout já foram vistos, e a configuração só pode ser aprovada na confirmatória.

| Combinação | Taxa fora da amostra | Wilson inf. | Meses acima | Apertados | Holdout (taxa / Wilson inf.) | Critérios (só leitura) |
|---|---|---|---|---|---|---|
| BTC 1m | 54,59% (23.447 operações) | 53,95% | 64% | 38,7% | 52,63% / 50,93% | não passaria |
| BTC 5m | 52,83% (8.369) | 51,76% | 29% | 11,0% | 50,17% / 46,92% (907) | não passaria |
| ETH 1m | 53,58% (19.962) | 52,89% | 57% | 16,1% | 54,40% / 53,24% | não passaria |
| ETH 5m | **55,04%** (22.927) | 54,40% | **93%** | 8,8% | 54,12% / 52,99% | não passaria |

As estratégias simples ficaram entre 50,08% e 50,50%. Comparado com a rodada principal, a mudança está mais na execução do que no modelo:

- **No 5m, a vantagem depende muito de entrar logo.** O ETH 5m sobe de 51,45% para 55,04%, com 93% dos meses acima do equilíbrio. Mesmo assim, o limite de Wilson (54,40%) fica abaixo de 54,76%, e o holdout (Wilson 52,99%) não confirma.
- **No 1m, a melhora é menor.** O BTC 1m vai de 53,74% para 54,59%, mas 39% das operações terminam apertadas.
- **A conclusão não muda:** nenhuma combinação passaria nos critérios nem nesse cenário mais favorável. O ETH 5m com entrada rápida é a hipótese mais promissora para a confirmatória, mas a aprovação depende dela. Como o resultado deste diagnóstico já é conhecido, ele não serve de evidência a favor.
