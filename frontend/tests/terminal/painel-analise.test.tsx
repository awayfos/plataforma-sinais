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

  it("valores nulos da análise aparecem como — sem quebrar", () => {
    const analise = {
      ...analiseTeste,
      forca_tendencia: null,
      volume: { relativo: null, pressao_compradora: null },
      indicadores: { rsi: null, macd_hist: null, estoc_k: null, bb_pct: null, atr: null },
      price_action: { impulso: null, desaceleracao: null, lateral: false },
    };
    render(<PainelAnalise analise={analise} modo="avancado" aberto />);
    expect(screen.getByTestId("volume-relativo")).toHaveTextContent("—");
    expect(screen.getByTestId("pressao-compradora")).toHaveTextContent("—");
    expect(screen.queryByRole("img", { name: /Compradores/ })).toBeNull();
    expect(screen.getByText("RSI").closest("div")).toHaveTextContent("—");
    expect(screen.queryByText(/NaN/)).toBeNull();
  });

  it("t é a abertura do último candle de 1m fechado: mostra o intervalo do minuto", () => {
    render(<PainelAnalise analise={{ ...analiseTeste, t: Date.parse("2026-11-25T13:30:00Z") }} modo="essencial" aberto />);
    expect(screen.getByTestId("minuto-analise")).toHaveTextContent("10:30–10:31");
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
