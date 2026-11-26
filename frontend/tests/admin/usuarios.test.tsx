import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { GestaoUsuarios } from "@/components/admin/GestaoUsuarios";
import { caminho, simularFetch, type Chamada } from "../apoio/fetch";

const usuarios = [
  { id: 7, email: "ana@teste.local", nome: "Ana Souza", papel: "cliente", status: "ativo", assinatura: { plano: "Mensal", status: "ativa", vence_em: Date.parse("2026-12-25T03:00:00Z") }, assinatura_id: 31 },
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
    if (p === "/api/admin/assinaturas/31/encerrar" && c.metodo === "POST")
      return { corpo: { id: 31, usuario_id: 7, plano_id: 1, inicio: 0, fim: Date.now(), origem: "manual" } };
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

  it("encerrar assinatura pede confirmação e envia POST /api/admin/assinaturas/{id}/encerrar", async () => {
    const chamadas = backend();
    const user = userEvent.setup();
    render(<GestaoUsuarios />);
    const linha = (await screen.findByText("ana@teste.local")).closest("tr")!;
    // só quem tem assinatura vigente tem o botão
    const bia = screen.getByText("bia@teste.local").closest("tr")!;
    expect(within(bia).queryByRole("button", { name: /Encerrar assinatura/ })).toBeNull();
    await user.click(within(linha).getByRole("button", { name: "Encerrar assinatura de Ana Souza" }));
    expect(within(linha).getByText(/O acesso termina na hora/)).toBeInTheDocument();
    expect(chamadas.some((c) => c.url.includes("/encerrar"))).toBe(false);
    await user.click(within(linha).getByRole("button", { name: "Cancelar" }));
    expect(chamadas.some((c) => c.url.includes("/encerrar"))).toBe(false);
    await user.click(within(linha).getByRole("button", { name: "Encerrar assinatura de Ana Souza" }));
    await user.click(within(linha).getByRole("button", { name: "Confirmar encerramento" }));
    await vi.waitFor(() => {
      const post = chamadas.find((c) => c.url.includes("/encerrar"))!;
      expect(post.metodo).toBe("POST");
      expect(caminho(post.url)).toBe("/api/admin/assinaturas/31/encerrar");
    });
    // a lista é recarregada depois da ação
    await vi.waitFor(() => expect(chamadas.filter((c) => caminho(c.url) === "/api/admin/usuarios").length).toBeGreaterThan(1));
  });

  it("redefinir senha envia PATCH {senha_temporaria} validada", async () => {
    const chamadas = backend();
    const user = userEvent.setup();
    render(<GestaoUsuarios />);
    const linha = (await screen.findByText("ana@teste.local")).closest("tr")!;
    await user.click(within(linha).getByRole("button", { name: "Redefinir senha de Ana Souza" }));
    const campo = within(linha).getByLabelText("Nova senha temporária");
    await user.type(campo, "curta");
    await user.click(within(linha).getByRole("button", { name: "Salvar senha" }));
    expect(within(linha).getByRole("alert")).toHaveTextContent("A senha temporária precisa ter pelo menos 10 caracteres.");
    expect(chamadas.some((c) => c.metodo === "PATCH")).toBe(false);
    await user.clear(campo);
    await user.type(campo, "temporaria-123");
    await user.click(within(linha).getByRole("button", { name: "Salvar senha" }));
    await vi.waitFor(() => {
      const patch = chamadas.find((c) => c.metodo === "PATCH")!;
      expect(caminho(patch.url)).toBe("/api/admin/usuarios/7");
      expect(patch.corpo).toEqual({ senha_temporaria: "temporaria-123" });
    });
  });

  it("criar envia o id numérico do plano", async () => {
    const chamadas = backend();
    const user = userEvent.setup();
    render(<GestaoUsuarios />);
    await screen.findByText("ana@teste.local");
    await user.click(screen.getByRole("button", { name: "Novo usuário" }));
    const form = screen.getByRole("form", { name: "Novo usuário" });
    await user.type(within(form).getByLabelText("E-mail"), "novo@teste.local");
    await user.type(within(form).getByLabelText("Nome"), "Novo Cliente");
    await user.type(within(form).getByLabelText("Senha temporária"), "temporaria-123");
    await user.click(within(form).getByRole("button", { name: "Criar usuário" }));
    await vi.waitFor(() => expect(chamadas.find((c) => c.metodo === "POST")?.corpo).toMatchObject({ plano: 1 }));
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
