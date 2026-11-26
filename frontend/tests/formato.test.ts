import { describe, expect, it } from "vitest";
import { formatarContagemVela, formatarDuracao, formatarHora, formatarPercentual, formatarPreco } from "@/lib/formato";

describe("formato (pt-BR)", () => {
  it("preço em string decimal sem perder precisão", () => {
    expect(formatarPreco("43250.12000000")).toBe("43.250,12");
    expect(formatarPreco("0.00012300")).toBe("0,000123");
    expect(formatarPreco("100")).toBe("100,00");
    expect(formatarPreco("1234567.5")).toBe("1.234.567,50");
    expect(formatarPreco(43250.5)).toBe("43.250,50");
  });

  it("percentual com vírgula", () => {
    expect(formatarPercentual(0.57)).toBe("57,0%");
    expect(formatarPercentual(0.5376, 2)).toBe("53,76%");
  });

  it("duração de contagem regressiva", () => {
    expect(formatarDuracao(24_000)).toBe("0:24");
    expect(formatarDuracao(23_100)).toBe("0:24");
    expect(formatarDuracao(85_000)).toBe("1:25");
    expect(formatarDuracao(3_723_000)).toBe("1:02:03");
    expect(formatarDuracao(-5)).toBe("0:00");
  });

  it("contagem até o fechamento do candle (rótulo do eixo de preço)", () => {
    expect(formatarContagemVela(37_000)).toBe("00:37");
    expect(formatarContagemVela(36_100)).toBe("00:37");
    expect(formatarContagemVela(14 * 60_000 + 5_000)).toBe("14:05");
    expect(formatarContagemVela(3 * 3_600_000 + 61_000)).toBe("03:01:01");
    expect(formatarContagemVela(2 * 86_400_000 + 3_600_000)).toBe("2d 01:00");
    expect(formatarContagemVela(-1)).toBe("00:00");
  });

  it("hora em Brasília", () => {
    expect(formatarHora(Date.parse("2026-11-25T13:30:29Z"))).toBe("10:30:29");
  });
});
