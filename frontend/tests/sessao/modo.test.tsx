import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AlternadorModo } from "@/components/sessao/AlternadorModo";
import { ProvedorSessao } from "@/components/sessao/ProvedorSessao";
import { usuarioTeste } from "../apoio/dados";
import { caminho, simularFetch } from "../apoio/fetch";

vi.mock("next/navigation", async () => {
  const { roteador } = await import("../apoio/navegacao");
  return { useRouter: () => roteador, usePathname: () => "/terminal" };
});

describe("AlternadorModo", () => {
  it("salva o modo escolhido nas preferências", async () => {
    document.cookie = "sinais_csrf=abc; path=/";
    const chamadas = simularFetch((c) => {
      if (caminho(c.url) === "/api/eu" && c.metodo === "GET") return { corpo: usuarioTeste };
      if (caminho(c.url) === "/api/eu/preferencias") return { corpo: { ...usuarioTeste, modo: "avancado" } };
      return undefined;
    });
    const user = userEvent.setup();
    render(
      <ProvedorSessao>
        <AlternadorModo />
      </ProvedorSessao>,
    );
    const essencial = await screen.findByRole("radio", { name: "Essencial" });
    await vi.waitFor(() => expect(essencial).toBeChecked());
    await user.click(screen.getByRole("radio", { name: "Avançado" }));
    await vi.waitFor(() => expect(screen.getByRole("radio", { name: "Avançado" })).toBeChecked());
    const patch = chamadas.find((c) => c.metodo === "PATCH");
    expect(patch?.corpo).toEqual({ modo: "avancado" });
    expect(patch?.headers["x-csrf-token"]).toBe("abc");
  });
});
