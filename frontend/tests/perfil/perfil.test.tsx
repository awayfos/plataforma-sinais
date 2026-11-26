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
    const chamadas = simularFetch((c) => {
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
    // resumo dos últimos 30 dias de todos os ativos: sem simbolo (aceito pelo backend)
    await vi.waitFor(() => expect(chamadas.some((c) => caminho(c.url) === "/api/sinais/historico")).toBe(true));
    const h = chamadas.find((c) => caminho(c.url) === "/api/sinais/historico")!;
    expect(new URL(h.url, "http://x").searchParams.has("simbolo")).toBe(false);
  });
});
