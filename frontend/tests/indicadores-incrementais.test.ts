import { describe, expect, it } from "vitest";
import { bollinger, ema, macd, rsi, vwap } from "@/lib/indicadores";
import { IndicadoresIncrementais } from "@/lib/indicadoresIncrementais";

function aleatorio(semente: number) {
  let x = semente;
  return () => {
    x = (x * 1103515245 + 12345) % 2 ** 31;
    return x / 2 ** 31;
  };
}

function serie(n: number) {
  const r = aleatorio(7);
  let preco = 100;
  const dia = Date.parse("2026-11-25T22:00:00Z"); // cruza 00:00 UTC (VWAP reinicia)
  return Array.from({ length: n }, (_, i) => {
    preco += (r() - 0.5) * 2;
    return { t: dia + i * 60_000, h: preco + r(), l: preco - r(), c: preco, v: 1 + r() * 10 };
  });
}

function comparar(a: (number | null)[], b: (number | null)[]) {
  expect(a).toHaveLength(b.length);
  a.forEach((v, i) => {
    if (b[i] === null) expect(v).toBeNull();
    else expect(v).toBeCloseTo(b[i]!, 8);
  });
}

describe("IndicadoresIncrementais", () => {
  it("após ticks (substituições) e novas barras, bate com o cálculo completo", () => {
    const final = serie(200);
    const inc = new IndicadoresIncrementais();
    inc.carregar(final.slice(0, 150));
    for (let i = 150; i < 200; i++) {
      const alvo = final[i]!;
      // três ticks em formação antes do valor final da barra
      inc.aplicar({ ...alvo, c: alvo.c + 1, v: alvo.v / 3 });
      inc.aplicar({ ...alvo, c: alvo.c - 1, v: alvo.v / 2 });
      inc.aplicar(alvo);
    }
    const c = final.map((x) => x.c);
    const s = inc.series();
    comparar(s.ema9, ema(c, 9));
    comparar(s.ema21, ema(c, 21));
    const b = bollinger(c, 20, 2);
    comparar(s.bbSup, b.superior);
    comparar(s.bbMedia, b.media);
    comparar(s.bbInf, b.inferior);
    comparar(s.vwap, vwap(final));
    comparar(s.rsi, rsi(c, 14));
    const m = macd(c);
    comparar(s.macd, m.macd);
    comparar(s.macdSinal, m.sinal);
    comparar(s.macdHist, m.histograma);
  });

  it("aplicar informa o índice e se a barra é nova", () => {
    const inc = new IndicadoresIncrementais();
    inc.carregar(serie(30));
    const ultimo = serie(31)[30]!;
    expect(inc.aplicar(ultimo)).toMatchObject({ indice: 30, nova: true });
    expect(inc.aplicar({ ...ultimo, c: 1 })).toMatchObject({ indice: 30, nova: false });
  });

  it("oficial atrasado de uma barra anterior recalcula dali em diante e bate com o cálculo completo", () => {
    const final = serie(120);
    const inc = new IndicadoresIncrementais();
    const previa = final.map((x, i) => (i === 117 ? { ...x, c: x.c + 3, h: x.h + 3 } : x));
    inc.carregar(previa); // barra 117 ainda com o valor dos ticks, 118 e 119 já em formação
    expect(inc.aplicar(final[117]!)).toEqual({ indice: 117, nova: false, desde: 117 });
    const c = final.map((x) => x.c);
    const s = inc.series();
    comparar(s.ema9, ema(c, 9));
    comparar(s.ema21, ema(c, 21));
    comparar(s.bbMedia, bollinger(c, 20, 2).media);
    comparar(s.vwap, vwap(final));
    comparar(s.rsi, rsi(c, 14));
    const m = macd(c);
    comparar(s.macd, m.macd);
    comparar(s.macdSinal, m.sinal);
    comparar(s.macdHist, m.histograma);
  });

  it("barra anterior que não existe na série é ignorada", () => {
    const inc = new IndicadoresIncrementais();
    const base = serie(30);
    inc.carregar(base);
    const r = inc.aplicar({ ...base[10]!, t: base[10]!.t + 1 });
    expect(r).toEqual({ indice: 29, nova: false, desde: 30 });
  });
});

