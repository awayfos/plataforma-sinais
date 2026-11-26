import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ListaAtivos } from "@/components/terminal/ListaAtivos";

const ativos = [
  { simbolo: "BTCUSDT", nome: "Bitcoin", classe: "cripto", aberto: true },
  { simbolo: "ETHUSDT", nome: "Ethereum", classe: "cripto", aberto: true },
  { simbolo: "XAUUSD", nome: "Ouro", classe: "metal", aberto: false },
];

describe("ListaAtivos", () => {
  it("marca o selecionado e troca ao clicar", async () => {
    const aoSelecionar = vi.fn();
    render(<ListaAtivos ativos={ativos} selecionado="BTCUSDT" aoSelecionar={aoSelecionar} />);
    expect(screen.getByRole("button", { name: /Bitcoin/ })).toHaveAttribute("aria-current", "true");
    await userEvent.setup().click(screen.getByRole("button", { name: /Ethereum/ }));
    expect(aoSelecionar).toHaveBeenCalledWith("ETHUSDT");
  });

  it("ativo fechado aparece como Fechado e desabilitado", () => {
    render(<ListaAtivos ativos={ativos} selecionado="BTCUSDT" aoSelecionar={() => {}} />);
    const ouro = screen.getByRole("button", { name: /Ouro/ });
    expect(ouro).toBeDisabled();
    expect(ouro).toHaveTextContent("Fechado");
  });
});
