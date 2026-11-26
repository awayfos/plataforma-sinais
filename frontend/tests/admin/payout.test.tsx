import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { EditorPayout } from "@/components/admin/EditorPayout";
import { caminho, simularFetch } from "../apoio/fetch";

const lista = [
  { simbolo: "BTCUSDT", expiracao: "1m", payout: 0.86 },
  { simbolo: "BTCUSDT", expiracao: "5m", payout: 0.88 },
];

describe("EditorPayout", () => {
  it("mostra o equilíbrio, valida a faixa e envia a lista inteira com PUT", async () => {
    const chamadas = simularFetch((c) =>
      caminho(c.url) === "/api/admin/corretoras/exnova/payout"
        ? { corpo: c.metodo === "PUT" ? c.corpo : lista }
        : undefined,
    );
    const user = userEvent.setup();
    render(<EditorPayout />);
    const campo = await screen.findByLabelText("Payout BTCUSDT 1 min");
    expect(campo).toHaveValue(86);
    expect(screen.getByText("53,76%")).toBeInTheDocument();

    await user.clear(campo);
    await user.type(campo, "120");
    await user.click(screen.getByRole("button", { name: "Salvar payouts" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Payout deve estar entre 1% e 100%.");
    expect(chamadas.some((c) => c.metodo === "PUT")).toBe(false);

    await user.clear(campo);
    await user.type(campo, "87");
    await user.click(screen.getByRole("button", { name: "Salvar payouts" }));
    await vi.waitFor(() => {
      const put = chamadas.find((c) => c.metodo === "PUT")!;
      expect(put.corpo).toEqual([
        { simbolo: "BTCUSDT", expiracao: "1m", payout: 0.87 },
        { simbolo: "BTCUSDT", expiracao: "5m", payout: 0.88 },
      ]);
    });
  });
});
