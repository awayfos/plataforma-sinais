import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { FormSenha } from "@/components/perfil/FormSenha";
import { caminho, simularFetch } from "../apoio/fetch";

async function preencher(atual: string, nova: string, confirmacao: string) {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("Senha atual"), atual);
  await user.type(screen.getByLabelText("Nova senha"), nova);
  await user.type(screen.getByLabelText("Confirme a nova senha"), confirmacao);
  await user.click(screen.getByRole("button", { name: "Alterar senha" }));
}

describe("FormSenha", () => {
  it("bloqueia senha nova com menos de 10 caracteres", async () => {
    const chamadas = simularFetch(() => ({ status: 204 }));
    render(<FormSenha />);
    await preencher("antiga-123", "curta", "curta");
    expect(screen.getByRole("alert")).toHaveTextContent("A nova senha precisa ter pelo menos 10 caracteres.");
    expect(chamadas).toHaveLength(0);
  });

  it("bloqueia confirmação diferente", async () => {
    const chamadas = simularFetch(() => ({ status: 204 }));
    render(<FormSenha />);
    await preencher("antiga-123", "nova-senha-forte", "outra-senha-forte");
    expect(screen.getByRole("alert")).toHaveTextContent("As senhas não coincidem.");
    expect(chamadas).toHaveLength(0);
  });

  it("envia e confirma o sucesso", async () => {
    const chamadas = simularFetch((c) => (caminho(c.url) === "/api/eu/senha" ? { status: 204 } : undefined));
    render(<FormSenha />);
    await preencher("antiga-123", "nova-senha-forte", "nova-senha-forte");
    expect(await screen.findByRole("status")).toHaveTextContent("Senha alterada. As outras sessões foram encerradas.");
    expect(chamadas[0]!.metodo).toBe("POST");
    expect(chamadas[0]!.corpo).toEqual({ senha_atual: "antiga-123", senha_nova: "nova-senha-forte" });
  });
});
