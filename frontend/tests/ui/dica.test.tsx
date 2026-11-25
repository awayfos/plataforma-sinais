import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { Dica } from "@/components/ui/Dica";
import { glossario } from "@/lib/glossario";

describe("Dica (aprenda)", () => {
  it("mostra a explicação ao clicar e fecha com Esc", async () => {
    const user = userEvent.setup();
    render(<Dica termo="rsi" />);
    const botao = screen.getByRole("button", { name: /aprenda: rsi/i });
    expect(screen.queryByRole("tooltip")).toBeNull();
    await user.click(botao);
    const tip = screen.getByRole("tooltip");
    expect(tip).toHaveTextContent(glossario.rsi.texto);
    expect(botao).toHaveAttribute("aria-expanded", "true");
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("tooltip")).toBeNull();
  });

  it("todo termo do glossário tem título e texto", () => {
    for (const item of Object.values(glossario)) {
      expect(item.titulo.length).toBeGreaterThan(0);
      expect(item.texto.length).toBeGreaterThan(20);
    }
  });
});
