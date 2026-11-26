// Indicadores do gráfico calculados barra a barra: carregar() percorre a série uma vez; aplicar() recalcula
// só a última posição (tick em formação) ou anexa uma nova, a partir do estado da barra anterior.
// Mesmos parâmetros e resultados de lib/indicadores.ts (conferido nos testes).
import type { CandleNumerico, Serie } from "./indicadores";

const P_EMA_RAPIDA = 9;
const P_EMA_LENTA = 21;
const P_BB = 20;
const MULT_BB = 2;
const P_RSI = 14;
const P_MACD_R = 12;
const P_MACD_L = 26;
const P_MACD_S = 9;

export interface SeriesIndicadoras {
  ema9: Serie;
  ema21: Serie;
  bbSup: Serie;
  bbMedia: Serie;
  bbInf: Serie;
  vwap: Serie;
  rsi: Serie;
  macd: Serie;
  macdSinal: Serie;
  macdHist: Serie;
}

export class IndicadoresIncrementais {
  private k: CandleNumerico[] = [];
  private s: SeriesIndicadoras = vazias();
  private e12: Serie = [];
  private e26: Serie = [];
  private ganho: Serie = [];
  private perda: Serie = [];
  private somaPV: number[] = [];
  private somaV: number[] = [];
  private inicioMacd = -1;

  carregar(candles: CandleNumerico[]): void {
    this.k = [];
    this.s = vazias();
    this.e12 = [];
    this.e26 = [];
    this.ganho = [];
    this.perda = [];
    this.somaPV = [];
    this.somaV = [];
    this.inicioMacd = -1;
    for (const c of candles) this.aplicar(c);
  }

  series(): SeriesIndicadoras {
    return this.s;
  }

  /** Mesmo t da última barra → recalcula a última; t maior → anexa. Devolve o índice calculado. */
  aplicar(c: CandleNumerico): { indice: number; nova: boolean } {
    const ultimo = this.k.at(-1);
    const nova = !ultimo || c.t > ultimo.t;
    if (!nova && c.t < ultimo!.t) return { indice: this.k.length - 1, nova: false };
    const i = nova ? this.k.length : this.k.length - 1;
    this.k[i] = c;
    this.calcular(i);
    return { indice: i, nova };
  }

  ponto(i: number): { [K in keyof SeriesIndicadoras]: number | null } {
    const s = this.s;
    return {
      ema9: s.ema9[i] ?? null,
      ema21: s.ema21[i] ?? null,
      bbSup: s.bbSup[i] ?? null,
      bbMedia: s.bbMedia[i] ?? null,
      bbInf: s.bbInf[i] ?? null,
      vwap: s.vwap[i] ?? null,
      rsi: s.rsi[i] ?? null,
      macd: s.macd[i] ?? null,
      macdSinal: s.macdSinal[i] ?? null,
      macdHist: s.macdHist[i] ?? null,
    };
  }

  private fechamento(i: number): number {
    return this.k[i]!.c;
  }

  private ema(serie: Serie, i: number, periodo: number, valor: (j: number) => number, inicio = 0): number | null {
    const j = i - inicio;
    if (j < periodo - 1) return null;
    if (j === periodo - 1) {
      let soma = 0;
      for (let x = inicio; x <= i; x++) soma += valor(x);
      return soma / periodo;
    }
    const k = 2 / (periodo + 1);
    return valor(i) * k + serie[i - 1]! * (1 - k);
  }

  private calcular(i: number): void {
    const s = this.s;
    const c = (j: number) => this.fechamento(j);
    s.ema9[i] = this.ema(s.ema9, i, P_EMA_RAPIDA, c);
    s.ema21[i] = this.ema(s.ema21, i, P_EMA_LENTA, c);

    // Bollinger: janela das últimas P_BB barras.
    if (i >= P_BB - 1) {
      let soma = 0;
      for (let j = i - P_BB + 1; j <= i; j++) soma += c(j);
      const media = soma / P_BB;
      let q = 0;
      for (let j = i - P_BB + 1; j <= i; j++) q += (c(j) - media) ** 2;
      const desvio = Math.sqrt(q / P_BB);
      s.bbMedia[i] = media;
      s.bbSup[i] = media + MULT_BB * desvio;
      s.bbInf[i] = media - MULT_BB * desvio;
    } else {
      s.bbMedia[i] = s.bbSup[i] = s.bbInf[i] = null;
    }

    // VWAP acumulado desde 00:00 UTC.
    const k = this.k[i]!;
    const mesmoDia = i > 0 && Math.floor(this.k[i - 1]!.t / 86_400_000) === Math.floor(k.t / 86_400_000);
    const pv = ((k.h + k.l + k.c) / 3) * k.v;
    this.somaPV[i] = (mesmoDia ? this.somaPV[i - 1]! : 0) + pv;
    this.somaV[i] = (mesmoDia ? this.somaV[i - 1]! : 0) + k.v;
    s.vwap[i] = this.somaV[i]! > 0 ? this.somaPV[i]! / this.somaV[i]! : null;

    // RSI de Wilder.
    if (i < P_RSI) {
      this.ganho[i] = this.perda[i] = null;
      s.rsi[i] = null;
    } else {
      let g: number;
      let p: number;
      if (i === P_RSI) {
        g = 0;
        p = 0;
        for (let j = 1; j <= P_RSI; j++) {
          const d = c(j) - c(j - 1);
          if (d > 0) g += d;
          else p -= d;
        }
        g /= P_RSI;
        p /= P_RSI;
      } else {
        const d = c(i) - c(i - 1);
        g = (this.ganho[i - 1]! * (P_RSI - 1) + Math.max(d, 0)) / P_RSI;
        p = (this.perda[i - 1]! * (P_RSI - 1) + Math.max(-d, 0)) / P_RSI;
      }
      this.ganho[i] = g;
      this.perda[i] = p;
      s.rsi[i] = p === 0 ? (g === 0 ? 50 : 100) : g === 0 ? 0 : 100 - 100 / (1 + g / p);
    }

    // MACD 12/26/9.
    this.e12[i] = this.ema(this.e12, i, P_MACD_R, c);
    this.e26[i] = this.ema(this.e26, i, P_MACD_L, c);
    const linha = this.e12[i] !== null && this.e26[i] !== null ? this.e12[i]! - this.e26[i]! : null;
    s.macd[i] = linha;
    if (linha !== null && this.inicioMacd < 0) this.inicioMacd = i;
    s.macdSinal[i] =
      linha === null || this.inicioMacd < 0 ? null : this.ema(s.macdSinal, i, P_MACD_S, (j) => s.macd[j]!, this.inicioMacd);
    s.macdHist[i] = linha !== null && s.macdSinal[i] !== null ? linha - s.macdSinal[i]! : null;
  }
}

function vazias(): SeriesIndicadoras {
  return { ema9: [], ema21: [], bbSup: [], bbMedia: [], bbInf: [], vwap: [], rsi: [], macd: [], macdSinal: [], macdHist: [] };
}
