import { describe, expect, it, vi } from "vitest";
import { AgrupadorQuadros } from "@/lib/agrupador";

describe("AgrupadorQuadros (requestAnimationFrame)", () => {
  it("vários ticks no mesmo quadro viram uma única descarga", () => {
    const quadros: (() => void)[] = [];
    const descarregar = vi.fn();
    const a = new AgrupadorQuadros<number>(descarregar, (fn) => {
      quadros.push(fn);
    });
    for (let i = 0; i < 10; i++) a.enfileirar(i);
    expect(quadros).toHaveLength(1);
    expect(descarregar).not.toHaveBeenCalled();
    quadros[0]!();
    expect(descarregar).toHaveBeenCalledTimes(1);
    expect(descarregar).toHaveBeenCalledWith([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]);
    a.enfileirar(10);
    expect(quadros).toHaveLength(2);
    quadros[1]!();
    expect(descarregar).toHaveBeenLastCalledWith([10]);
  });

  it("descartar cancela o quadro pendente", () => {
    const quadros: (() => void)[] = [];
    const descarregar = vi.fn();
    const a = new AgrupadorQuadros<number>(descarregar, (fn) => {
      quadros.push(fn);
    });
    a.enfileirar(1);
    a.descartar();
    quadros[0]!();
    expect(descarregar).not.toHaveBeenCalled();
  });

  it("fila limitada: guarda só os mais recentes (aba em segundo plano)", () => {
    const quadros: (() => void)[] = [];
    const descarregar = vi.fn();
    const a = new AgrupadorQuadros<number>(descarregar, (fn) => void quadros.push(fn), 3);
    for (let i = 0; i < 10; i++) a.enfileirar(i);
    quadros[0]!();
    expect(descarregar).toHaveBeenCalledWith([7, 8, 9]);
  });
});
