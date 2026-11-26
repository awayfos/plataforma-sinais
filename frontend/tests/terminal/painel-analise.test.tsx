import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PainelAnalise } from "@/components/terminal/PainelAnalise";
import { analiseTeste } from "../apoio/dados";

describe("PainelAnalise", () => {
  it("mostra as frases do resumo", () => {
    render(<PainelAnalise analise={analiseTeste} modo="essencial" aberto />);
    for (const frase of analiseTeste.resumo) expect(screen.getByText(frase)).toBeInTheDocument();
  });

  it("resistência tocada 3+ vezes é difícil de romper; suporte com 2 toques não", () => {
    render(<PainelAnalise analise={analiseTeste} modo="essencial" aberto />);
    const res = screen.getByTestId("regiao-resistencia");
    expect(res).toHaveTextContent("difícil de romper");
    expect(res).toHaveTextContent("5 toques");
    expect(screen.getByTestId("regiao-suporte")).not.toHaveTextContent("difícil de romper");
  });

  it("tendência por tempo gráfico em texto (não só cor)", () => {
    render(<PainelAnalise analise={analiseTeste} modo="essencial" aberto />);
    expect(screen.getByTestId("tendencia-1m")).toHaveTextContent("Alta");
    expect(screen.getByTestId("tendencia-15m")).toHaveTextContent("Lateral");
    expect(screen.getByTestId("tendencia-1h")).toHaveTextContent("Baixa");
  });

  it("tempo gráfico ausente na análise mostra — e não Lateral", () => {
    const { "1h": _omitido, ...semUmaHora } = analiseTeste.tendencia;
    void _omitido;
    const analise = { ...analiseTeste, tendencia: semUmaHora as typeof analiseTeste.tendencia };
    render(<PainelAnalise analise={analise} modo="essencial" aberto />);
    expect(screen.getByTestId("tendencia-1h")).toHaveTextContent("—");
    expect(screen.getByTestId("tendencia-1h")).not.toHaveTextContent("Lateral");
  });

  it("evento de estrutura legível", () => {
    render(<PainelAnalise analise={analiseTeste} modo="essencial" aberto />);
    expect(screen.getByText(/Rompimento de estrutura para cima/)).toBeInTheDocument();
  });

  it("modo Essencial esconde os indicadores; Avançado mostra", () => {
    const { rerender } = render(<PainelAnalise analise={analiseTeste} modo="essencial" aberto />);
    expect(screen.queryByText("RSI")).toBeNull();
    rerender(<PainelAnalise analise={analiseTeste} modo="avancado" aberto />);
    expect(screen.getByText("RSI")).toBeInTheDocument();
    expect(screen.getByText("61,2")).toBeInTheDocument();
  });

  it("mercado fechado não mostra análise", () => {
    render(<PainelAnalise analise={null} modo="essencial" aberto={false} />);
    expect(screen.getByText(/Mercado fechado/)).toBeInTheDocument();
  });
});
