import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CartaoSinal } from "@/components/terminal/CartaoSinal";
import type { Sinal } from "@/lib/api/tipos";
import { caminho, simularFetch } from "../apoio/fetch";

const base: Sinal = {
  expiracao: "1m",
  direcao: "COMPRA",
  probabilidade: 0.571,
  n_validacao: 412,
  motivo: "",
  janela_ate: Date.parse("2026-11-25T13:30:29Z"),
  invalidacao: "Fechamento abaixo de 43.010",
  modelo: "m1",
};

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date", "setInterval", "clearInterval"] });
  vi.setSystemTime(new Date("2026-11-25T13:30:05Z"));
  simularFetch((c) =>
    caminho(c.url) === "/api/sinais/historico"
      ? {
          corpo: [
            { id: "a", simbolo: "BTCUSDT", expiracao: "1m", direcao: "COMPRA", gerado_em: 0, preco_referencia: "1", resultado: "WIN", apertado: false },
            { id: "b", simbolo: "BTCUSDT", expiracao: "1m", direcao: "VENDA", gerado_em: 0, preco_referencia: "1", resultado: "LOSS", apertado: true },
            { id: "c", simbolo: "BTCUSDT", expiracao: "5m", direcao: "VENDA", gerado_em: 0, preco_referencia: "1", resultado: "LOSS", apertado: false },
          ],
        }
      : undefined,
  );
});

afterEach(() => vi.useRealTimers());

describe("CartaoSinal", () => {
  it("mostra direção, probabilidade com n, invalidação e contagem regressiva", () => {
    render(<CartaoSinal sinal={base} simbolo="BTCUSDT" />);
    expect(screen.getByRole("heading", { name: /COMPRA/ })).toHaveTextContent("1 min");
    expect(screen.getByText("57,1%")).toBeInTheDocument();
    expect(screen.getByText(/n = 412/)).toBeInTheDocument();
    expect(screen.getByText("Fechamento abaixo de 43.010")).toBeInTheDocument();
    expect(screen.getByTestId("contagem")).toHaveTextContent("0:24");
    expect(screen.getByText(/10:30:29/)).toBeInTheDocument();
  });

  it("vira 'Fora da janela, não entre' quando a janela passa com a tela aberta", () => {
    render(<CartaoSinal sinal={base} simbolo="BTCUSDT" />);
    expect(screen.queryByText("Fora da janela, não entre")).toBeNull();
    act(() => vi.advanceTimersByTime(25_000));
    expect(screen.getByText("Fora da janela, não entre")).toBeInTheDocument();
  });

  it("expiração curta tem o aviso de entrada precisa", () => {
    render(<CartaoSinal sinal={base} simbolo="BTCUSDT" />);
    expect(screen.getByTestId("nota-entrada")).toHaveTextContent(/exige entrada precisa/);
  });

  it("estatísticas do histórico da mesma expiração", async () => {
    render(<CartaoSinal sinal={base} simbolo="BTCUSDT" />);
    await act(async () => { await Promise.resolve(); await Promise.resolve(); await Promise.resolve(); });
    await vi.waitFor(() => expect(screen.getByTestId("historico-sinal")).toHaveTextContent("50,0%"));
    expect(screen.getByTestId("historico-sinal")).toHaveTextContent("n = 2");
  });

  it("tolerância de preço só aparece se o backend enviar", () => {
    const { rerender } = render(<CartaoSinal sinal={base} simbolo="BTCUSDT" />);
    expect(screen.queryByText(/Tolerância de preço/)).toBeNull();
    rerender(<CartaoSinal sinal={{ ...base, tolerancia_preco: "12.5", preco_referencia: "43250.10" }} simbolo="BTCUSDT" />);
    expect(screen.getByText(/Tolerância de preço/)).toBeInTheDocument();
    expect(screen.getByText(/43\.250,10/)).toBeInTheDocument();
  });
});
