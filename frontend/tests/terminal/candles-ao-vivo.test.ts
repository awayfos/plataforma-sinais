import { describe, expect, it } from "vitest";
import { legendaVisivel, mesclarCandle, tempoDoGrafico } from "@/lib/candles";

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

describe("tempoDoGrafico", () => {
  const meiaNoite = Date.parse("2026-11-25T00:00:00Z");
  it("intradiário mostra horário de Brasília (UTC−3)", () => {
    expect(tempoDoGrafico(meiaNoite, "1m")).toBe(meiaNoite / 1000 - 3 * 3600);
    expect(tempoDoGrafico(meiaNoite, "4h")).toBe(meiaNoite / 1000 - 3 * 3600);
  });
  it("1d e 1w não deslocam (senão a barra cai no dia anterior)", () => {
    expect(tempoDoGrafico(meiaNoite, "1d")).toBe(meiaNoite / 1000);
    expect(tempoDoGrafico(meiaNoite, "1w")).toBe(meiaNoite / 1000);
  });
});

describe("legendaVisivel", () => {
  const serie = [c(1, "1"), c(2, "2")];
  it("usa o candle em foco só se for da mesma série", () => {
    expect(legendaVisivel({ chave: "BTCUSDT:1m", candle: c(1, "1") }, "BTCUSDT:1m", serie)?.c).toBe("1");
    expect(legendaVisivel({ chave: "ETHUSDT:1m", candle: c(9, "9") }, "BTCUSDT:1m", serie)?.c).toBe("2");
    expect(legendaVisivel(null, "BTCUSDT:1m", serie)?.c).toBe("2");
    expect(legendaVisivel(null, "BTCUSDT:1m", [])).toBeNull();
  });
});
