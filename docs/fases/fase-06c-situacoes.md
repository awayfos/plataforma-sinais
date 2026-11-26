# Fase 6c — Motor de Situações (pesquisa)

- **Status:** concluída. **Resultado: nenhuma situação aprovada.** Todas ficam "Histórico — não validado".
- **Design:** `docs/superpowers/specs/2026-11-26-motor-situacoes-design.md`
- **Plano:** `docs/superpowers/plans/2026-11-26-motor-situacoes.md`
- **Pré-registro:** `docs/laboratorio/2026-11-26-situacoes-pre-registro.md` (commit `fb8bc3a`)
- **Contagem:** `docs/laboratorio/2026-11-26-situacoes-contagem.md` (run 45819149884)
- **Resultado:** `docs/laboratorio/2026-11-26-situacoes-resultado.md` (run 45886523156)

## 1. Objetivo

Testar a hipótese do cliente: em situações específicas de price action, com fundamento, pode existir
vantagem que some quando o modelo tenta prever todo minuto (Fases 6 e 6b).

## 2. O que foi construído (`backend/src/sinais/situacoes/`)

| Parte | Arquivo | O que faz |
|---|---|---|
| Parâmetros | `parametros.py` | Todos os números pré-registrados (S1–S8, 10 variações, execução, critérios) |
| Base | `base.py` | Arrays de 1m, pressão compradora, ATR, blocos fechados de 5m/15m e o mapa 1m → último bloco fechado |
| Zonas | `zonas.py` | Níveis de pivôs de 1m com o instante de cada toque (toques em 4 h, ordem do toque, tempo entre toques) |
| Detectores | `detectores.py` | S1 exaustão no topo novo; S2 falso rompimento; S3/S3b rompimento com força + reteste; S4 reteste após BOS no 5m; S5 CHoCH após tendência esgotada; S6/S6a rejeição repetida na máxima de 4 h (15m); S7 divergência no extremo de 15m; S8 extremo de lateralização. Todos com espelho |
| Motor | `motor.py` | Roda tudo e acrescenta distância a S/R em ATR, queda de pressão, confluências e conflito (§9b.6) |
| Simulação | `simulacao.py` | Entrada em decisão + 2..10 s (sorteio por hash do instante: independe do lote), tolerância de 0,5 × ATR(1m), vencimento da Exnova válido só no prazo de compra, preço de 1 s, um sinal por vencimento |
| Liquidação | `liquidacao.py` | `RegistroSinal`: "VENDA · BTCUSDT · 15 min", entrada (instante e preço), vencimento, preço final e WIN/LOSS/EMPATE — o registro da futura área de sinais |
| Contagem | `contagem.py` | Ocorrências sem rótulo por chave (corte de 300) |
| Avaliação | `avaliacao.py`, `avaliacao_real.py` | Critérios §13.3, estratégias simples nas mesmas janelas, BH sobre a família inteira, "B supera A" |
| Camada B | `qualificadora.py`, `features_b.py` | HGB + isotônica por validação cruzada temporal, por variação × expiração, juntando espelhos e ativos; `fs-2` + contexto da situação |
| Rodadas | `relatorio.py`, `.github/workflows/situacoes.yml` | Contagem e avaliação no Actions (disparo manual), relatório no log |
| Confirmação | `confirmacao.py`, `.github/workflows/situacoes-confirmacao.yml` | Todo dia 3 reprocessa os meses fechados desde 2026-11 com o mesmo código e imprime o acumulado e os sinais liquidados |

**Causalidade:** `tests/regressao_vazamento/test_causalidade_situacoes.py` confere que os eventos com
decisão até *t*, com todo o contexto, são os mesmos com a série cortada em *t* (um corte no evento de cada
variação) e com o futuro embaralhado, e que os rompimentos de região não mudam com a série cortada (60
cortes). **Validado por mutação**: cinco vazamentos introduzidos de propósito fizeram os testes falharem —
S1 olhando a máxima do candle seguinte; bloco de 5m/15m em formação tratado como fechado; pivô de 15m de
S7 sem o atraso de confirmação; queda de pressão com candles futuros; toques de região sem confirmação do
pivô. **Simetria:** espelhar o preço espelha todos os eventos (mesmos instantes, topo ↔ fundo).

## 3. Ordem do trabalho (pré-registro)

1. Detectores e testes (sem dados reais).
2. Commit do pré-registro com todos os números (`fb8bc3a`).
3. Contagem sem rótulo: 84 das 120 chaves elegíveis; S5, S6 (4º toque ou mais) e S7 abaixo de 300 em todas
   as expirações e ativos, fora da avaliação confirmatória.
4. Rodada rotulada (A e B) uma vez, sem ajuste depois.

## 4. Resultado (payout 0,86, equilíbrio 53,76%)

- Nenhuma chave elegível tem Wilson inferior acima de 54,76% e nenhuma sobrevive a Benjamini-Hochberg.
  34 de 144 linhas elegíveis (A + B) têm taxa pontual acima do equilíbrio.
- S2, S3/S3b, S4 e S8 ficam na faixa das estratégias simples (45,8% a 53,3% em 15 min).
- S1 (estratégia do cliente) é a mais próxima no ETH: 54,4–54,6% em 15 min e 55,9% em 30 min (fundo,
  898 operações), sem significância.
- S6a (2º–3º toque, o exemplo do cliente): 50,8–51,4% em 15 min.
- S7 teve 57–60% com 229–257 operações, mas estava fora pelo corte pré-registrado: é só hipótese.
- A camada B não supera a camada A de forma útil: poucos sinais, calibração ruim onde o treino é pequeno.

Detalhes e a tabela completa: `docs/laboratorio/2026-11-26-situacoes-resultado.md`.

## 5. Desvios declarados

- Depois da 1ª rodada (que parou antes de qualquer resultado), a camada B passou a descartar colunas
  totalmente vazias no treino, porque o HGB do scikit-learn 1.9 falha nelas (commit `f28098f`).
- Holdout mais fraco que o da Fase 6 (≥ 50 operações e taxa > equilíbrio) e mês com ≥ 10 operações,
  ambos fixados no pré-registro, porque situações são raras; o holdout já tinha sido visto.
- A confirmação de candidatas da camada B não foi implementada (não houve candidata B).

## 6. Confirmação em meses novos

A lista de candidatas (`docs/laboratorio/situacoes-candidatas.json`) está vazia. O job mensal roda mesmo
assim e informa que não há o que confirmar. O teste de fumaça (run 45890175639, só com 2026-10, mês já
visto, sem valor de confirmação) baixou os dados, reprocessou S1 e S8 e imprimiu 555 sinais liquidados com
o registro completo.

## 7. Próximos passos (decisão do cliente)

1. Painel "Situação agora" com as situações como "Histórico — não validado" e esta estatística, sem botão.
2. Se o cliente quiser, novo pré-registro **só para meses novos**: S7 e uma S6 de 1m nos moldes do gráfico
   que ele mostrou (mesma zona de topo tocada várias vezes em ~2 h, cada toque recuando). A S6/S6a desta
   fase usa máximas de 15m.
3. Fontes novas de informação (livro de ofertas, fluxo, funding) e o preço de referência da Exnova.
4. Motor ao vivo, modo sombra, endpoints e UI depois do merge do backend e do frontend.
