import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { FormLogin, destinoSeguro } from "@/components/auth/FormLogin";
import { usuarioTeste } from "../apoio/dados";
import { caminho, simularFetch } from "../apoio/fetch";
import { reiniciarRoteador, roteador } from "../apoio/navegacao";

vi.mock("next/navigation", async () => {
  const { roteador } = await import("../apoio/navegacao");
  return { useRouter: () => roteador, usePathname: () => "/login" };
});

beforeEach(() => reiniciarRoteador());

async function preencher(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("E-mail"), "admin@teste.local");
  await user.type(screen.getByLabelText("Senha"), "senha-muito-forte");
  await user.click(screen.getByRole("button", { name: "Entrar" }));
}

describe("FormLogin", () => {
  it("mostra a mensagem do servidor quando as credenciais são inválidas", async () => {
    simularFetch(() => ({ status: 401, corpo: { erro: { codigo: "credenciais_invalidas", mensagem: "E-mail ou senha incorretos." } } }));
    const user = userEvent.setup();
    render(<FormLogin />);
    await preencher(user);
    expect(await screen.findByRole("alert")).toHaveTextContent("E-mail ou senha incorretos.");
    expect(roteador.replace).not.toHaveBeenCalled();
  });

  it("pede o código TOTP quando o servidor exige e reenvia com ele", async () => {
    let tentativa = 0;
    const chamadas = simularFetch((c) => {
      if (caminho(c.url) !== "/api/auth/login") return undefined;
      tentativa += 1;
      if (tentativa === 1) return { status: 401, corpo: { erro: { codigo: "totp_necessario", mensagem: "Informe o código." } } };
      return { corpo: { usuario: { ...usuarioTeste, papel: "admin" } } };
    });
    const user = userEvent.setup();
    render(<FormLogin proximo="/historico" />);
    await preencher(user);
    const campo = await screen.findByLabelText("Código de verificação");
    expect(campo).toHaveAttribute("autocomplete", "one-time-code");
    await user.type(campo, "123456");
    await user.click(screen.getByRole("button", { name: "Verificar" }));
    await vi.waitFor(() => expect(roteador.replace).toHaveBeenCalledWith("/historico"));
    expect(chamadas[1]!.corpo).toEqual({ email: "admin@teste.local", senha: "senha-muito-forte", totp: "123456" });
  });

  it("conta bloqueada (423) mostra a mensagem", async () => {
    simularFetch(() => ({ status: 423, corpo: { erro: { codigo: "conta_bloqueada", mensagem: "Conta bloqueada." } } }));
    const user = userEvent.setup();
    render(<FormLogin />);
    await preencher(user);
    expect(await screen.findByRole("alert")).toHaveTextContent("Conta bloqueada.");
  });
});

describe("destinoSeguro", () => {
  it("aceita só caminhos internos", () => {
    expect(destinoSeguro("/historico")).toBe("/historico");
    expect(destinoSeguro("//evil.com")).toBe("/terminal");
    expect(destinoSeguro("https://evil.com")).toBe("/terminal");
    expect(destinoSeguro("/login")).toBe("/terminal");
    expect(destinoSeguro(undefined)).toBe("/terminal");
  });

  it("rejeita caracteres de controle e barra invertida (o navegador os remove e vira outro host)", () => {
    expect(destinoSeguro("/\t/evil.com")).toBe("/terminal");
    expect(destinoSeguro("/\n/evil.com")).toBe("/terminal");
    expect(destinoSeguro("/\r/evil.com")).toBe("/terminal");
    expect(destinoSeguro("/\\evil.com")).toBe("/terminal");
    expect(destinoSeguro("/\\/evil.com")).toBe("/terminal");
  });

  it("mantém caminho interno codificado, consulta e âncora", () => {
    expect(destinoSeguro("/%09/evil.com")).toBe("/%09/evil.com");
    expect(destinoSeguro("/historico?simbolo=BTCUSDT#topo")).toBe("/historico?simbolo=BTCUSDT#topo");
  });
});
