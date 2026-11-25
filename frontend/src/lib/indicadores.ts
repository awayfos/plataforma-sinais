// Indicadores para sobreposições do gráfico (só exibição; a análise oficial vem do backend).
export type Serie = (number | null)[];

export function sma(valores: number[], periodo: number): Serie {
  const saida: Serie = new Array(valores.length).fill(null);
  let soma = 0;
  for (let i = 0; i < valores.length; i++) {
    soma += valores[i]!;
    if (i >= periodo) soma -= valores[i - periodo]!;
    if (i >= periodo - 1) saida[i] = soma / periodo;
  }
  return saida;
}

/** EMA semeada pela média simples dos primeiros `periodo` valores. */
export function ema(valores: number[], periodo: number): Serie {
  const saida: Serie = new Array(valores.length).fill(null);
  if (valores.length < periodo) return saida;
  const k = 2 / (periodo + 1);
  let anterior = 0;
  for (let i = 0; i < periodo; i++) anterior += valores[i]!;
  anterior /= periodo;
  saida[periodo - 1] = anterior;
  for (let i = periodo; i < valores.length; i++) {
    anterior = valores[i]! * k + anterior * (1 - k);
    saida[i] = anterior;
  }
  return saida;
}

export function bollinger(valores: number[], periodo = 20, mult = 2): { media: Serie; superior: Serie; inferior: Serie } {
  const media = sma(valores, periodo);
  const superior: Serie = new Array(valores.length).fill(null);
  const inferior: Serie = new Array(valores.length).fill(null);
  for (let i = periodo - 1; i < valores.length; i++) {
    const m = media[i]!;
    let soma = 0;
    for (let j = i - periodo + 1; j <= i; j++) soma += (valores[j]! - m) ** 2;
    const desvio = Math.sqrt(soma / periodo);
    superior[i] = m + mult * desvio;
    inferior[i] = m - mult * desvio;
  }
  return { media, superior, inferior };
}

export interface CandleNumerico {
  t: number;
  h: number;
  l: number;
  c: number;
  v: number;
}

/** VWAP acumulado a partir de 00:00 UTC de cada dia. */
export function vwap(candles: CandleNumerico[]): Serie {
  const saida: Serie = [];
  let dia = -1;
  let pv = 0;
  let vol = 0;
  for (const k of candles) {
    const d = Math.floor(k.t / 86_400_000);
    if (d !== dia) {
      dia = d;
      pv = 0;
      vol = 0;
    }
    pv += ((k.h + k.l + k.c) / 3) * k.v;
    vol += k.v;
    saida.push(vol > 0 ? pv / vol : null);
  }
  return saida;
}

/** RSI de Wilder. */
export function rsi(valores: number[], periodo = 14): Serie {
  const saida: Serie = new Array(valores.length).fill(null);
  if (valores.length <= periodo) return saida;
  let ganho = 0;
  let perda = 0;
  for (let i = 1; i <= periodo; i++) {
    const d = valores[i]! - valores[i - 1]!;
    if (d > 0) ganho += d;
    else perda -= d;
  }
  ganho /= periodo;
  perda /= periodo;
  saida[periodo] = valorRsi(ganho, perda);
  for (let i = periodo + 1; i < valores.length; i++) {
    const d = valores[i]! - valores[i - 1]!;
    ganho = (ganho * (periodo - 1) + Math.max(d, 0)) / periodo;
    perda = (perda * (periodo - 1) + Math.max(-d, 0)) / periodo;
    saida[i] = valorRsi(ganho, perda);
  }
  return saida;
}

function valorRsi(ganho: number, perda: number): number {
  if (perda === 0) return ganho === 0 ? 50 : 100;
  if (ganho === 0) return 0;
  return 100 - 100 / (1 + ganho / perda);
}

export function macd(valores: number[], rapida = 12, lenta = 26, periodoSinal = 9): { macd: Serie; sinal: Serie; histograma: Serie } {
  const er = ema(valores, rapida);
  const el = ema(valores, lenta);
  const linha: Serie = valores.map((_, i) => (er[i] !== null && el[i] !== null ? er[i]! - el[i]! : null));
  const inicio = linha.findIndex((v) => v !== null);
  const sinal: Serie = new Array(valores.length).fill(null);
  if (inicio >= 0) {
    const compacta = linha.slice(inicio) as number[];
    const es = ema(compacta, periodoSinal);
    es.forEach((v, i) => {
      sinal[inicio + i] = v;
    });
  }
  const histograma: Serie = linha.map((v, i) => (v !== null && sinal[i] !== null ? v - sinal[i]! : null));
  return { macd: linha, sinal, histograma };
}
