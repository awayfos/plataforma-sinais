import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TabelaSinais } from "@/components/terminal/TabelaSinais";
import type { Sinal } from "@/lib/api/tipos";
import { aguardar } from "../apoio/dados";

const compra: Sinal = {
  expiracao: "1m",
  direcao: "COMPRA",
  probabilidade: 0.57,
  n_validacao: 412,
  motivo: "",
  janela_ate: null,
  invalidacao: null,
  modelo: "m1",
};

describe("TabelaSinais", () => {
  it("mostra uma linha por expiração, em ordem, mesmo com lista parcial", () => {
    render(<TabelaSinais sinais={[aguardar("60m"), compra]} />);
    const linhas = screen.getAllByRole("row").slice(1);
    expect(linhas).toHaveLength(5);
    expect(linhas.map((l) => within(l).getByRole("rowheader").textContent)).toEqual([
      "1 min",
      "5 min",
      "15 min",
      "30 min",
      "1 h",
    ]);
    expect(linhas[1]).toHaveTextContent("Sem dados");
  });

  it("COMPRA mostra probabilidade calibrada e n", () => {
    render(<TabelaSinais sinais={[compra]} />);
    const linha = screen.getAllByRole("row")[1]!;
    expect(linha).toHaveTextContent("COMPRA");
    expect(linha).toHaveTextContent("57,0%");
    expect(linha).toHaveTextContent("n = 412");
  });

  it("AGUARDAR mostra o motivo e não inventa probabilidade", () => {
    render(<TabelaSinais sinais={[aguardar("5m")]} />);
    const linha = screen.getAllByRole("row")[2]!;
    expect(linha).toHaveTextContent("AGUARDAR");
    expect(linha).toHaveTextContent("Nenhum modelo validado para esta expiração");
    expect(linha).not.toHaveTextContent("%");
  });

  it("sem lista mostra estado de carregamento", () => {
    render(<TabelaSinais sinais={null} />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });
});
