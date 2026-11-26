import { describe, expect, it } from "vitest";
import { proximoFechamento } from "@/lib/candles";
import { formatarContagemVela } from "@/lib/formato";

const M = 60_000;

describe("proximoFechamento (contagem do rótulo de preço)", () => {
  it("barra em formação fecha uma duração depois da abertura", () => {
    expect(proximoFechamento(10 * M, M, 10 * M + 15_000)).toBe(11 * M);
  });

  it("sem tick novo depois do fim do período, avança pelo relógio em vez de parar em 00:00", () => {
    // última barra (fechada ou não) abriu em 10:00; já são 10:01:20 e nenhum tick de 10:01 chegou
    const fecha = proximoFechamento(10 * M, M, 11 * M + 20_000);
    expect(fecha).toBe(12 * M);
    expect(formatarContagemVela(fecha - (11 * M + 20_000))).toBe("00:40");
    // vários períodos sem tick (mercado parado)
    expect(proximoFechamento(10 * M, 5 * M, 31 * M)).toBe(35 * M);
    // exatamente na virada: já conta o período seguinte inteiro
    expect(proximoFechamento(10 * M, M, 11 * M)).toBe(12 * M);
  });
});
