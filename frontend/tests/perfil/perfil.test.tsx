import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Perfil } from "@/components/perfil/Perfil";
import { ProvedorSessao } from "@/components/sessao/ProvedorSessao";
import { usuarioTeste } from "../apoio/dados";
import { caminho, simularFetch } from "../apoio/fetch";

vi.mock("next/navigation", async () => {
  const { roteador } = await import("../apoio/navegacao");
  return { useRouter: () => roteador, usePathname: () => "/perfil" };
});

describe("Perfil", () => {
  it("usuário sem assinatura (plano null) mostra 'Sem plano'", async () => {
    simularFetch((c) => {
      if (caminho(c.url) === "/api/eu")
        return { corpo: { ...usuarioTeste, assinatura: { plano: null, status: "vencida", vence_em: null } } };
      if (caminho(c.url) === "/api/sinais/historico") return { corpo: [] };
      return undefined;
    });
    render(
      <ProvedorSessao>
        <Perfil />
      </ProvedorSessao>,
    );
    expect(await screen.findByTestId("perfil-plano")).toHaveTextContent("Sem plano");
  });
});
