import { describe, expect, it } from "vitest";
import { bollinger, ema, macd, rsi, sma, vwap } from "@/lib/indicadores";

describe("indicadores (valores calculados à mão)", () => {
  it("SMA 3", () => {
    expect(sma([1, 2, 3, 4, 5], 3)).toEqual([null, null, 2, 3, 4]);
  });

  it("EMA 3 semeada pela média simples", () => {
    expect(ema([1, 2, 3, 4, 5], 3)).toEqual([null, null, 2, 3, 4]);
    const e = ema([2, 4, 6, 8], 2); // k = 2/3: semente 3; 6→5; 8→7
    expect(e[1]).toBeCloseTo(3);
    expect(e[2]).toBeCloseTo(5);
    expect(e[3]).toBeCloseTo(7);
  });

  it("série menor que o período não tem valor", () => {
    expect(ema([1, 2], 5)).toEqual([null, null]);
  });

  it("RSI só com ganhos é 100 e com série constante é 50", () => {
    const subindo = Array.from({ length: 20 }, (_, i) => i + 1);
    expect(rsi(subindo, 14)[14]).toBe(100);
    expect(rsi(subindo, 14)[13]).toBeNull();
    expect(rsi(Array(20).fill(10), 14)[19]).toBe(50);
  });

  it("RSI só com perdas é 0", () => {
    const caindo = Array.from({ length: 20 }, (_, i) => 100 - i);
    expect(rsi(caindo, 14)[19]).toBe(0);
  });

  it("Bollinger de série constante tem bandas iguais à média", () => {
    const b = bollinger(Array(25).fill(7), 20, 2);
    expect(b.media[24]).toBe(7);
    expect(b.superior[24]).toBe(7);
    expect(b.inferior[24]).toBe(7);
    expect(b.media[18]).toBeNull();
  });

  it("Bollinger usa desvio populacional", () => {
    const b = bollinger([1, 3], 2, 2); // média 2, desvio 1
    expect(b.superior[1]).toBe(4);
    expect(b.inferior[1]).toBe(0);
  });

  it("VWAP de candles iguais é o preço típico e reinicia a cada dia UTC", () => {
    const dia = Date.parse("2026-11-25T00:00:00Z");
    const v = vwap([
      { t: dia, h: 12, l: 8, c: 10, v: 5 },
      { t: dia + 60_000, h: 12, l: 8, c: 10, v: 5 },
      { t: dia + 86_400_000, h: 30, l: 30, c: 30, v: 1 },
    ]);
    expect(v).toEqual([10, 10, 30]);
  });

  it("VWAP sem volume é nulo", () => {
    expect(vwap([{ t: 0, h: 1, l: 1, c: 1, v: 0 }])).toEqual([null]);
  });

  it("MACD de série constante é zero", () => {
    const m = macd(Array(60).fill(100), 12, 26, 9);
    expect(m.macd[25]).toBe(0);
    expect(m.macd[24]).toBeNull();
    expect(m.sinal[33]).toBe(0);
    expect(m.sinal[32]).toBeNull();
    expect(m.histograma[59]).toBe(0);
  });
});
