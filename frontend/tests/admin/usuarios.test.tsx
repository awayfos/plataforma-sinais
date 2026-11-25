import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { GestaoUsuarios } from "@/components/admin/GestaoUsuarios";
import { caminho, simularFetch, type Chamada } from "../apoio/fetch";

const usuarios = [
  { id: 7, email: "ana@teste.local", nome: "Ana Souza", papel: "cliente", status: "ativo", assinatura: { plano: "Mensal", status: "ativa", vence_em: Date.parse("2026-12-25T03:00:00Z") } },
  { id: 8, email: "bia@teste.local", nome: "Bia Lima", papel: "cliente", status: "bloqueado", assinatura: null },
];
const planos = [
  { id: 1, nome: "Mensal", duracao_dias: 30, preco_centavos: 9990, recursos: { ativos: ["BTCUSDT"], expiracoes: ["1m"], modo_avancado: true, cursos: false }, ativo: true },
];

function backend(): Chamada[] {
  return simularFetch((c) => {
    const p = caminho(c.url);
    if (p === "/api/admin/usuarios" && c.metodo === "GET") return { corpo: usuarios };
    if (p === "/api/admin/planos") return { corpo: planos };
    if (p.startsWith("/api/admin/usuarios/") && c.metodo === "PATCH") return { corpo: { ...usuarios[0], status: "bloqueado" } };
    if (p === "/api/admin/usuarios" && c.metodo === "POST") return { status: 201, corpo: usuarios[0] };
    return undefined;
  });
}

describe("GestaoUsuarios", () => {
  it("lista e busca", async () => {
    const chamadas = backend();
    const user = userEvent.setup();
    render(<GestaoUsuarios />);
    expect(await screen.findByText("ana@teste.local")).toBeInTheDocument();
    await user.type(screen.getByRole("searchbox", { name: "Buscar usuários" }), "ana{Enter}");
    await vi.waitFor(() =>
      expect(chamadas.some((c) => new URL(c.url, "http://x").searchParams.get("busca") === "ana")).toBe(true),
    );
  });

  it("bloquear pede confirmação e envia PATCH {status: bloqueado}", async () => {
    const chamadas = backend();
    const user = userEvent.setup();
    render(<GestaoUsuarios />);
    const linha = (await screen.findByText("ana@teste.local")).closest("tr")!;
    await user.click(within(linha).getByRole("button", { name: "Bloquear Ana Souza" }));
    expect(chamadas.some((c) => c.metodo === "PATCH")).toBe(false);
    await user.click(within(linha).getByRole("button", { name: "Confirmar bloqueio" }));
    await vi.waitFor(() => {
      const patch = chamadas.find((c) => c.metodo === "PATCH")!;
      expect(caminho(patch.url)).toBe("/api/admin/usuarios/7");
      expect(patch.corpo).toEqual({ status: "bloqueado" });
    });
  });

  it("criar valida a senha temporária", async () => {
    const chamadas = backend();
    const user = userEvent.setup();
    render(<GestaoUsuarios />);
    await screen.findByText("ana@teste.local");
    await user.click(screen.getByRole("button", { name: "Novo usuário" }));
    const form = screen.getByRole("form", { name: "Novo usuário" });
    await user.type(within(form).getByLabelText("E-mail"), "novo@teste.local");
    await user.type(within(form).getByLabelText("Nome"), "Novo Cliente");
    await user.type(within(form).getByLabelText("Senha temporária"), "curta");
    await user.click(within(form).getByRole("button", { name: "Criar usuário" }));
    expect(within(form).getByRole("alert")).toHaveTextContent("A senha temporária precisa ter pelo menos 10 caracteres.");
    expect(chamadas.some((c) => c.metodo === "POST")).toBe(false);
  });
});
