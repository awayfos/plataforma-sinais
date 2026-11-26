// Textos do ícone "aprenda" (design §5, item 7). Linguagem simples, sem promessa de resultado.

export const glossario = {
  tendencia: {
    titulo: "Tendência",
    texto: "Direção predominante do preço num tempo gráfico: alta (topos e fundos subindo), baixa (descendo) ou lateral (sem direção clara).",
  },
  adx: {
    titulo: "Força da tendência (ADX)",
    texto: "Mede quão forte é a tendência, não a direção. Abaixo de 20 costuma indicar mercado sem direção; acima de 25, tendência mais firme.",
  },
  suporte: {
    titulo: "Suporte",
    texto: "Região abaixo do preço onde compradores apareceram antes e o preço parou de cair. Quanto mais toques, mais difícil de romper.",
  },
  resistencia: {
    titulo: "Resistência",
    texto: "Região acima do preço onde vendedores apareceram antes e o preço parou de subir. Quanto mais toques, mais difícil de romper.",
  },
  distancia_atr: {
    titulo: "Distância em ATR",
    texto: "Quão longe o preço está da região, medido em ATRs (o tamanho médio de um candle). 0,5 ATR é metade de um candle típico.",
  },
  estrutura: {
    titulo: "Estrutura de mercado",
    texto: "Sequência de topos e fundos. BOS (quebra de estrutura) confirma a tendência atual; CHoCH (mudança de caráter) é o primeiro sinal de virada.",
  },
  volume_relativo: {
    titulo: "Volume relativo",
    texto: "Volume do momento comparado à média recente. 2× significa o dobro do normal: movimentos com volume alto tendem a ser mais confiáveis.",
  },
  pressao_compradora: {
    titulo: "Pressão compradora",
    texto: "Parte do volume executada por quem comprou a mercado (agressão). Acima de 50%, compradores mais agressivos que vendedores.",
  },
  impulso: {
    titulo: "Impulso",
    texto: "Força do movimento recente: candles grandes e na mesma direção indicam impulso forte.",
  },
  desaceleracao: {
    titulo: "Desaceleração",
    texto: "O movimento continua, mas com candles cada vez menores ou com pavios contrários. Costuma anteceder pausa ou reversão.",
  },
  lateral: {
    titulo: "Mercado lateral",
    texto: "Preço preso numa faixa, sem tendência. Sinais de direção costumam funcionar pior nessa condição.",
  },
  rsi: {
    titulo: "RSI (Índice de Força Relativa)",
    texto: "Oscilador de 0 a 100 que compara altas e baixas recentes. Acima de 70 é considerado sobrecomprado; abaixo de 30, sobrevendido.",
  },
  macd: {
    titulo: "MACD",
    texto: "Diferença entre duas médias móveis exponenciais (12 e 26). O histograma positivo indica força compradora crescente; negativo, vendedora.",
  },
  estocastico: {
    titulo: "Estocástico %K",
    texto: "Posição do fechamento dentro da faixa máxima–mínima recente, de 0 a 100. Perto de 100, fechando no topo da faixa.",
  },
  bollinger: {
    titulo: "Bandas de Bollinger",
    texto: "Média de 20 períodos com bandas a 2 desvios-padrão. %B mostra onde o preço está: 0 na banda inferior, 1 na superior.",
  },
  atr: {
    titulo: "ATR (amplitude média)",
    texto: "Tamanho médio dos candles recentes, em preço. Serve de régua para distâncias e para a tolerância de entrada.",
  },
  ema: {
    titulo: "Média móvel exponencial (EMA)",
    texto: "Média dos preços que dá mais peso aos mais recentes. No gráfico: EMA 9 (rápida) e EMA 21 (lenta).",
  },
  vwap: {
    titulo: "VWAP",
    texto: "Preço médio ponderado pelo volume desde o início do dia (UTC). Muito usado como referência de preço justo do dia.",
  },
  probabilidade: {
    titulo: "Probabilidade calibrada",
    texto: "Frequência com que sinais parecidos acertaram em dados que o modelo nunca viu. Calibrada significa que 57% acertaram perto de 57% das vezes. Não é garantia.",
  },
  amostra: {
    titulo: "Tamanho da amostra (n)",
    texto: "Quantos sinais fora da amostra sustentam a probabilidade. Quanto maior o n, mais confiável a estimativa.",
  },
  janela: {
    titulo: "Janela de entrada",
    texto: "Até quando a entrada ainda vale na corretora. Depois do prazo de compra, o vencimento muda e o sinal deixa de valer.",
  },
  tolerancia: {
    titulo: "Tolerância de preço",
    texto: "Distância máxima entre o preço de referência do sinal e o seu preço de entrada. Fora dela, não entre.",
  },
  invalidacao: {
    titulo: "Invalidação",
    texto: "Condição que anula o sinal antes da entrada. Se acontecer, ignore o sinal.",
  },
  aguardar: {
    titulo: "AGUARDAR",
    texto: "Não há vantagem comprovada agora para esta expiração. A plataforma só mostra COMPRA ou VENDA quando a combinação passou na validação estatística.",
  },
  apertado: {
    titulo: "Resultado apertado",
    texto: "Vencimento muito perto do preço de entrada. Pequenas diferenças entre a fonte de referência e a corretora podem inverter esse resultado.",
  },
  payout: {
    titulo: "Payout e equilíbrio",
    texto: "Retorno pago pela corretora numa vitória. Com payout r, é preciso acertar mais de 1/(1+r) para não perder dinheiro: 53,76% com 86%.",
  },
  expiracao: {
    titulo: "Expiração",
    texto: "Tempo até o vencimento da operação na corretora. Cada expiração tem seu próprio modelo e sua própria validação.",
  },
} as const satisfies Record<string, { titulo: string; texto: string }>;

export type TermoGlossario = keyof typeof glossario;
