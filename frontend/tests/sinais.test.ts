import { describe, expect, it } from "vitest";
import { estadoJanela, estatisticas, ordenarSinais } from "@/lib/sinais";
import type { SinalHistorico } from "@/lib/api/tipos";
import { aguardar } from "./apoio/dados";

describe("ordenarSinais", () => {
  it("devolve as 5 expirações em ordem, com null na que faltar", () => {
    const r = ordenarSinais([aguardar("60m"), aguardar("1m"), aguardar("15m")]);
    expect(r.map((x) => x.expiracao)).toEqual(["1m", "5m", "15m", "30m", "60m"]);
    expect(r[1]!.sinal).toBeNull();
    expect(r[0]!.sinal?.expiracao).toBe("1m");
  });
});

describe("estadoJanela", () => {
  it("dentro da janela mostra o restante", () => {
    expect(estadoJanela(10_000, 4_000)).toEqual({ dentro: true, restanteMs: 6_000 });
  });
  it("janela passada ou ausente está fora", () => {
    expect(estadoJanela(10_000, 10_001)).toEqual({ dentro: false, restanteMs: 0 });
    expect(estadoJanela(null, 0)).toEqual({ dentro: false, restanteMs: 0 });
  });
});

describe("estatisticas", () => {
  const h = (resultado: SinalHistorico["resultado"], apertado = false): SinalHistorico => ({
    id: Math.random().toString(),
    simbolo: "BTCUSDT",
    expiracao: "5m",
    direcao: "COMPRA",
    gerado_em: 0,
    preco_referencia: "1",
    resultado,
    apertado,
  });

  it("taxa = WIN / (WIN + LOSS); empate e sem dado à parte", () => {
    const s = estatisticas([h("WIN"), h("WIN"), h("LOSS"), h("TIE"), h("SEM_DADO"), h(null)]);
    expect(s).toEqual({ n: 4, win: 2, loss: 1, tie: 1, semDado: 1, pendentes: 1, apertados: 0, taxa: 2 / 3 });
  });

  it("AGUARDAR não entra nas estatísticas", () => {
    const espera = { ...h(null), direcao: "AGUARDAR" as const };
    expect(estatisticas([h("WIN"), espera]).pendentes).toBe(0);
  });

  it("sem operações decididas a taxa é nula", () => {
    expect(estatisticas([h("TIE")]).taxa).toBeNull();
  });
});
