# Motor de Situações — design

**Data:** 2026-11-26 · **Status:** aprovado pelo cliente ("continue", 2026-11-26)
**Complementa:** `2026-11-25-plataforma-sinais-design.md` (§12–§13 continuam valendo)
**Depende de:** PR #15 (Fase 6b: rótulos 1 s, microestrutura `fs-2`, avaliação v2) mergeado na `main`.

## 1. Intenção e o porquê

O cliente opera opções binárias (principalmente BTC, expiração de 15 min, Exnova) lendo **situações**:
o preço faz um topo novo, a pressão compradora perde força, começam as vendas, ele **espera o preço
confirmar** que quer cair e então vende. Ele quer que a IA pense assim — com fundamento (price action,
estrutura, regiões, toques, pressão de volume, indicadores) — e **só opere quando a situação tiver esse
nível de qualidade**, aprendendo com cada resultado.

Os testes das Fases 6 e 6b mostraram que um modelo que tenta prever **todo minuto** não tem vantagem com o
payout da Exnova (a vantagem se dilui na média). A hipótese deste design é a do cliente: **em situações
específicas, bem definidas, pode existir vantagem que some na média**. O produto entrega **direção com
fundamento e estatística honesta**, não promessa de lucro. "Sempre ganhar" não existe; o objetivo é operar
só onde há vantagem comprovada e desligar o que deixar de funcionar.

## 2. Objetivos, não objetivos, anti-objetivos

**Objetivos**
- Detectar ao vivo, de forma causal, um catálogo de situações com fundamento, cada uma com direção.
- Medir cada situação × expiração com a regra real da Exnova e entrada realista em 1 s.
- Uma camada de IA que, **dentro** de cada situação, qualifica a oportunidade usando confluências
  (não uma média de tudo) e só libera quando a probabilidade calibrada supera o limiar.
- Mostrar ao usuário o painel "Situação agora" com fundamento em texto e estatística (n, intervalo).
- Liberar o botão COMPRA/VENDA **somente** para situações aprovadas pelos critérios §13.3.
- Aprender continuamente: modo sombra ao vivo, retreino mensal, desligamento automático.

**Não objetivos (V1 deste motor)**: execução automática de ordens; martingale ou gestão de banca agressiva;
ativos além de BTCUSDT/ETHUSDT.

**Anti-objetivos (seria fracasso mesmo funcionando)**
- Testar centenas de variações até alguma "passar" (garimpo de dados).
- Mostrar estatística dentro da amostra como se fosse sinal.
- Liberar sinal com base em meses já vistos sem confirmação em meses novos.

## 3. Abordagens consideradas

| | Abordagem | Troca |
|---|---|---|
| A | Situações como regras explícitas, testadas uma a uma | Clara, explicável, pouco risco de autoengano; cada situação precisa ser escrita |
| B | A + IA qualificadora treinada só nos momentos da situação | Extrai mais da situação; só vale onde A mostra algo; risco de sobreajuste controlado por walk-forward |
| C | "Momentos parecidos" (vizinhos mais próximos) | Intuitivo, difícil de validar e instável |

**Escolhida: A + B** (decisão delegada pelo cliente: "quero que você decida o melhor caminho").
C descartada: difícil de provar e engana fácil.

## 4. Catálogo V1 de situações (pré-registrado)

Todas usam só candles **fechados** (1m e agregados 5m/15m/1h) e microestrutura de 1 s até o fim do minuto
da decisão. Toda situação tem o **espelho** (topo↔fundo, compra↔venda). "Região" = níveis de `analise/regioes.py`
com contagem de toques nas últimas 4 h. Pressão compradora = volume taker buy / volume total.

| Id | Nome | Gatilho (resumo) | Direção |
|---|---|---|---|
| S1 | **Exaustão no topo novo** (estratégia do cliente) | Máxima nova de 4 h; pressão ≥ 55% no rompimento; depois ≥ 2 de 3 candles 1m com pressão < 50%; **confirmação**: fechamento 1m abaixo da mínima do candle que fez o topo em até 10 min, sem nova máxima | Contra o rompimento |
| S2 | Falso rompimento | Rompe região com ≥ 3 toques em 4 h e fecha de volta dentro em ≤ 3 candles 1m | Contra |
| S3 | Rompimento com força + reteste | Fecha além de região com ≥ 3 toques, volume relativo ≥ 1,5 e pressão ≥ 60%; entrada no reteste que segura | A favor |
| S4 | Reteste após quebra de estrutura | BOS no 5m; recuo até o nível rompido; candle de rejeição (pavio/engolfo) | A favor |
| S5 | Mudança de caráter após tendência esgotada | CHoCH no 5m após tendência de 15m com ADX alto, com divergência de RSI | Contra a tendência anterior |
| S6 | Rejeição repetida na máxima/mínima (exemplo do cliente no gráfico de 15 min) | Máximas de candles de 15 min agrupadas na mesma zona (até 0,15 × ATR de 15m) com ≥ 3 toques em 4 h, cada toque recuando; novo toque na zona e, no 1m, rejeição: pressão compradora < 50% e fechamento de volta abaixo da zona | Contra (venda na máxima / compra na mínima) |
| S7 | Divergência no extremo | Topo/fundo de 15m com divergência RSI/MACD confirmada por inversão de pressão | Contra |
| S8 | Extremo de lateralização | ADX baixo, faixa definida; toque no extremo com rejeição | Para o meio da faixa |

Cada situação tem **no máximo 2 variações** de parâmetros escritas antes de qualquer resultado. Expirações:
**15 min (principal)**, 5 min e 30 min. Família de testes para Benjamini-Hochberg = todas as
situações × espelhos × variações × expirações.

**Antes de olhar resultados**, um diagnóstico só conta quantas vezes cada situação ocorre (sem rótulo).
Situação com menos de 300 ocorrências esperadas no período fica fora da avaliação confirmatória.

## 5. Camada B — IA qualificadora

- Para cada situação com ocorrências suficientes, um modelo (HistGradientBoosting + calibração isotônica,
  mesmo padrão da Fase 6) treinado **só nas linhas em que a situação disparou**.
- Variáveis: `fs-2` + contexto da situação (toques da região, distância em ATR ao próximo suporte/
  resistência, força da queda de pressão, horário, regime) + **confluências** (quantas outras situações
  concordam, alinhamento com a tendência de 15m/1h). Confluência entra como variável, não como média.
- Saída: probabilidade calibrada de a direção da situação vencer. Opera só acima do limiar escolhido no
  bloco de calibração (calibração isotônica e escolha do limiar em metades separadas do mês).
- Comparação obrigatória: situação pura (A) × situação + IA (B). B só é adotada se superar A fora da amostra.

## 6. Validação

- Walk-forward mensal da Fase 6/6b (6 treino / 1 calibração / 1 teste, purga pelo vencimento real,
  embargo 1 h), entrada sorteada em 1 s dentro da janela de compra da Exnova, payout 0,86.
- Critérios §13.3 por situação × expiração (n ≥ 300, Wilson inferior > p* + 1 p.p., ≥ 70% dos meses,
  BH, vence baselines, holdout).
- **Confirmação em meses novos** (a partir de 2026-11) via modo sombra é obrigatória antes de liberar
  sinal para clientes: holdout antigo já foi visto.

## 7. Aprendizado contínuo

- **Modo sombra**: o motor detecta ao vivo todas as situações, registra decisão, janela de entrada e
  liquida automaticamente (regra Exnova). Visível só para admin até a aprovação.
- **Retreino mensal** com campeão/desafiante (teste de duas proporções), como §13.
- **Desligamento automático**: situação aprovada cujo Wilson inferior dos últimos N sinais ao vivo cair
  abaixo de p* volta para "histórico" e o botão é bloqueado; aviso ao admin.

## 8. Na tela

- Painel **"Situação agora"** na tela do ativo: situações ativas, texto do fundamento gerado por template
  (sem números inventados) e estatística: "Nas 380 vezes parecidas, caiu em 15 min em 57% (52%–62%)".
- Selo **"Validado"** ou **"Histórico — não validado"**. COMPRA/VENDA só aparece em "Validado", com a
  janela de entrada e o aviso de entrada precisa.
- Página de transparência com o desempenho ao vivo de cada situação.

## 9. Decisões tomadas pelo designer (cliente pode corrigir)

- Janela de contexto de 4 h para topo/fundo novo e toques (vinda do exemplo do cliente).
- Limiares de pressão 55% / 50% / 60% e confirmação em até 10 min (S1), escritos antes dos testes.
- 15 min como expiração principal (preferência declarada do cliente; menos operações "apertadas").

## 9b. Decisões do designer após a revisão do construtor

1. **Entrada e duração.** A situação dispara no fechamento do candle de confirmação. Entrada sorteada entre
   decisão + 2 s e + 10 s, recusada se o preço andou mais de 0,5 × ATR(1m) (mesma regra pré-registrada na
   Fase 6b §7). Vencimento alinhado ao relógio da Exnova; a situação só é válida se a entrada cair dentro do
   prazo de compra da expiração (para 15 min: entre 5 e 15 min até o vencimento). A estatística registra o
   tempo restante; o texto diz "até o vencimento de HH:MM", não "em 15 min".
2. **Descoberta e confirmação.** Descoberta: walk-forward em 2024-11..2026-10 com o holdout 2026-08..10
   (já visto pela Fase 6; declarado). Confirmação: meses novos a partir de 2026-11, reprocessados dos arquivos
   mensais da Binance assim que cada mês fecha (equivalente ao modo sombra, mesmo código) **e** o modo sombra
   ao vivo em paralelo. Critério de confirmação: n ≥ 100 sinais não sobrepostos nos meses novos e Wilson
   inferior > p*. A família de testes da confirmação é separada da Fase 6b e declarada.
3. **Ativos.** BTC e ETH testados separadamente; o ativo entra na família de Benjamini-Hochberg; o corte de
   300 ocorrências vale por situação × espelho × variação × ativo × expiração, contando sinais não sobrepostos.
4. **Desligamento.** Regra do design principal §12.9: desliga quando o Wilson **superior** dos últimos 100
   sinais ao vivo fica abaixo de p*; alerta ao admin quando o inferior fica abaixo de p*.
5. **Camada B.** Só é tentada para combinações com ≥ 1.000 linhas de treino; um modelo por situação,
   juntando espelhos e ativos (id do espelho e do ativo como variáveis); calibração por validação cruzada
   temporal dentro do bloco de treino + mês de calibração para o limiar. As variantes B entram na família BH.
   "B supera A" = teste de duas proporções unilateral nos mesmos meses de teste, p < 0,05.
6. **Conflitos.** Um sinal ativo por ativo × expiração. Situações em direções opostas ao mesmo tempo →
   AGUARDAR com motivo "situações em conflito". n de cada situação conta sinais não sobrepostos (um por
   vencimento).
7. **Parâmetros de S2–S8.** O designer fixa os números (≤ 2 variações por situação) num commit de
   pré-registro **antes** da contagem de ocorrências. Depois da contagem nada é afrouxado: situação abaixo de
   300 sai da avaliação confirmatória.
8. **Dependência.** O trabalho começa após o merge do PR #15 (o ramo é rebaseado sobre a `main`).

## 9c. Acréscimos do cliente (2026-11-26)

1. **Cada toque enfraquece a resistência/suporte.** A ordem do toque (1º, 2º, 3º, 4º+) e o tempo entre
   toques entram como variáveis na camada B e como recorte em S6: variação S6a = 2º–3º toque (região ainda
   forte, venda na rejeição); S3 ganha a variação S3b = rompimento após ≥ 4 toques (região gasta, a favor do
   rompimento). Estatística por ordem do toque aparece no painel.
2. **O que o usuário vê.**
   - **No gráfico**: marcação de COMPRA/VENDA no candle e no preço exato da entrada, linha do vencimento e,
     ao vencer, o resultado (WIN/LOSS/EMPATE) desenhado no gráfico.
   - **Área de sinais**: cada sinal mostra ativo, direção, expiração ("VENDA · BTCUSDT · 15 min"), preço de
     entrada que a IA mandou, horário da entrada, vencimento, preço final e resultado WIN/LOSS/EMPATE,
     liquidado automaticamente pela regra da Exnova; histórico com taxa de acerto e n.
   - COMPRA/VENDA como sinal **só** para situações aprovadas. Situações ainda não aprovadas aparecem no painel
     "Situação agora" com fundamento e histórico fora da amostra, rótulo "Histórico — não validado", sem
     botão de entrada (opção A, recomendação do designer; o cliente respondeu "continue").

## 10. Deixado ao construtor

Implementação de cada detector, estrutura de módulos (`sinais/situacoes/`), formato de persistência do
modo sombra, endpoints e componentes de UI (seguindo `contrato-v1.md`, com acréscimos documentados).
