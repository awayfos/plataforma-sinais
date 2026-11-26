import { describe, expect, it } from "vitest";
import type { CandleAoVivo } from "@/lib/api/tipos";
import { SerieAoVivo } from "@/lib/serieAoVivo";

const CANAL = "candles:BTCUSDT:1m";
const k = (t: number, c: string, fechado = false): CandleAoVivo => ({ t, o: "1", h: "9", l: "0.5", c, v: "1", fechado });
const base = [
  { t: 0, o: "1", h: "2", l: "1", c: "1.5", v: "3" },
  { t: 60, o: "1.5", h: "2", l: "1", c: "1.8", v: "3" },
];

function nova() {
  const s = new SerieAoVivo();
  s.carregar(CANAL, base);
  return s;
}

describe("SerieAoVivo (fusão de ticks)", () => {
  it("tick de t novo anexa uma barra", () => {
    const s = nova();
    expect(s.aplicar(CANAL, k(120, "2"))).toMatchObject({ tipo: "anexado", indice: 2 });
    expect(s.candles).toHaveLength(3);
  });

  it("ticks de mesmo t substituem a última barra sem crescer a série", () => {
    const s = nova();
    s.aplicar(CANAL, k(120, "2"));
    for (let i = 0; i < 50; i++) expect(s.aplicar(CANAL, k(120, String(2 + i / 100)))).toMatchObject({ tipo: "substituido", indice: 2 });
    expect(s.candles).toHaveLength(3);
    expect(s.candles.at(-1)!.c).toBe("2.49");
  });

  it("tick mais antigo que a última barra é ignorado", () => {
    const s = nova();
    s.aplicar(CANAL, k(120, "2"));
    expect(s.aplicar(CANAL, k(60, "9")).tipo).toBe("ignorado");
    expect(s.candles[1]!.c).toBe("1.8");
  });

  it("fechado:true finaliza: tick em formação atrasado do mesmo t é ignorado", () => {
    const s = nova();
    s.aplicar(CANAL, k(120, "2"));
    expect(s.aplicar(CANAL, k(120, "2.1", true))).toMatchObject({ tipo: "substituido" });
    expect(s.aplicar(CANAL, k(120, "5")).tipo).toBe("ignorado");
    expect(s.candles.at(-1)).toMatchObject({ c: "2.1", fechado: true });
    expect(s.aplicar(CANAL, k(180, "2.2"))).toMatchObject({ tipo: "anexado", indice: 3 });
  });

  it("candle fechado do REST não é reaberto por tick em formação", () => {
    const s = nova();
    expect(s.aplicar(CANAL, k(60, "7")).tipo).toBe("ignorado");
  });

  it("ticks do canal antigo (troca de tempo gráfico) são descartados", () => {
    const s = nova();
    s.carregar("candles:BTCUSDT:5m", [{ t: 0, o: "1", h: "2", l: "1", c: "1", v: "1" }]);
    expect(s.aplicar(CANAL, k(120, "2")).tipo).toBe("ignorado");
    expect(s.candles).toHaveLength(1);
  });

  it("recarregar o REST no mesmo canal (ressincronização) mantém a barra em formação mais nova", () => {
    const s = nova();
    s.aplicar(CANAL, k(120, "2"));
    s.carregar(CANAL, [...base, { t: 120, o: "1", h: "3", l: "1", c: "2.5", v: "9" }]);
    // o REST agora tem 120 fechado; a formação de 180 chega pelo snapshot
    expect(s.aplicar(CANAL, k(180, "2.6"))).toMatchObject({ tipo: "anexado", indice: 3 });
    s.carregar(CANAL, [...base, { t: 120, o: "1", h: "3", l: "1", c: "2.5", v: "9" }]);
    expect(s.candles.map((x) => x.t)).toEqual([0, 60, 120, 180]);
  });

  it("aplicarLote devolve cada barra tocada uma vez, em ordem", () => {
    const s = nova();
    const lote = [k(120, "2"), k(120, "2.1"), k(120, "2.2"), k(180, "2.3"), k(180, "2.4")].map((tick) => ({ canal: CANAL, tick }));
    expect(s.aplicarLote(lote)).toEqual([2, 3]);
    expect(s.candles.at(-1)!.c).toBe("2.4");
  });
});
