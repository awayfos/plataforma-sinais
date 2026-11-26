import { act, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { PrecoAoVivo } from "@/components/terminal/PrecoAoVivo";
import { lerPreco, publicarPreco, redefinirPrecos } from "@/lib/precos";

beforeEach(() => redefinirPrecos());

describe("preço ao vivo", () => {
  it("guarda a direção em relação ao preço anterior", () => {
    publicarPreco("BTCUSDT", "100.00");
    expect(lerPreco("BTCUSDT")).toMatchObject({ preco: "100.00", direcao: 0 });
    publicarPreco("BTCUSDT", "101.00");
    expect(lerPreco("BTCUSDT")).toMatchObject({ direcao: 1 });
    publicarPreco("BTCUSDT", "99.5");
    expect(lerPreco("BTCUSDT")).toMatchObject({ direcao: -1 });
  });

  it("mesmo preço não gera nova publicação", () => {
    publicarPreco("ETHUSDT", "10");
    const antes = lerPreco("ETHUSDT")!.seq;
    publicarPreco("ETHUSDT", "10.00");
    expect(lerPreco("ETHUSDT")!.seq).toBe(antes);
  });

  it("componente pisca para cima e para baixo", () => {
    render(<PrecoAoVivo simbolo="BTCUSDT" />);
    expect(screen.getByTestId("preco-BTCUSDT")).toHaveTextContent("—");
    act(() => publicarPreco("BTCUSDT", "43250.10"));
    act(() => publicarPreco("BTCUSDT", "43251.00"));
    const el = screen.getByTestId("preco-BTCUSDT");
    expect(el).toHaveTextContent("43.251,00");
    expect(el.className).toMatch(/piscar-alta/);
    act(() => publicarPreco("BTCUSDT", "43200.00"));
    expect(screen.getByTestId("preco-BTCUSDT").className).toMatch(/piscar-baixa/);
  });
});
