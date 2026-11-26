import { afterEach, describe, expect, it } from "vitest";
import { AMOSTRAS_RELOGIO, deslocamentoAtual, redefinirRelogio, registrarHoraServidor } from "@/lib/relogio";

const BASE = Date.parse("2026-11-25T13:30:00Z");
const data = (ms: number) => new Date(ms).toUTCString();

afterEach(() => redefinirRelogio());

describe("relógio do servidor", () => {
  it("a primeira amostra já define o deslocamento (meio do segundo do Date)", () => {
    registrarHoraServidor(data(BASE + 10_000), BASE);
    expect(deslocamentoAtual()).toBe(10_500);
  });

  it("usa a mediana das últimas amostras: uma resposta lenta isolada não mexe na contagem", () => {
    for (let i = 0; i < 4; i++) registrarHoraServidor(data(BASE + i * 1000 + 2_000), BASE + i * 1000);
    expect(deslocamentoAtual()).toBe(2_500);
    // resposta que ficou 3 s presa na rede: o Date é antigo em relação ao recebimento
    registrarHoraServidor(data(BASE + 5_000), BASE + 8_000);
    expect(deslocamentoAtual()).toBe(2_500);
  });

  it("guarda só as últimas amostras: uma mudança real do relógio acaba prevalecendo", () => {
    for (let i = 0; i < AMOSTRAS_RELOGIO; i++) registrarHoraServidor(data(BASE + 2_000), BASE);
    for (let i = 0; i < AMOSTRAS_RELOGIO; i++) registrarHoraServidor(data(BASE + 9_000), BASE);
    expect(deslocamentoAtual()).toBe(9_500);
  });

  it("cabeçalho ausente ou inválido é ignorado", () => {
    registrarHoraServidor(null, BASE);
    registrarHoraServidor("lixo", BASE);
    expect(deslocamentoAtual()).toBe(0);
  });
});
