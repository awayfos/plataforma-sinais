import { describe, expect, it } from "vitest";
import { mesclarCandle } from "@/lib/candles";

const c = (t: number, close: string) => ({ t, o: "1", h: "2", l: "0.5", c: close, v: "10" });

describe("mesclarCandle", () => {
  it("substitui o candle em formação de mesmo t", () => {
    const r = mesclarCandle([c(1, "1"), c(2, "1.5")], c(2, "1.7"));
    expect(r.map((x) => x.c)).toEqual(["1", "1.7"]);
  });

  it("anexa um candle novo", () => {
    expect(mesclarCandle([c(1, "1")], c(2, "1.2")).map((x) => x.t)).toEqual([1, 2]);
  });

  it("ignora candle mais antigo que o último (mensagem atrasada)", () => {
    const base = [c(5, "1"), c(6, "1")];
    expect(mesclarCandle(base, c(3, "9"))).toBe(base);
  });

  it("lista vazia recebe o candle", () => {
    expect(mesclarCandle([], c(1, "1"))).toHaveLength(1);
  });
});
