import { expect, test } from "@playwright/test";
import { BASE, simularBackend, usuarioAdmin } from "./mocks";

test("rota protegida sem sessão vai para o login; admin entra com TOTP e chega ao terminal", async ({ page, context }) => {
  await simularBackend(page, { usuario: usuarioAdmin });
  const tentativas: unknown[] = [];
  await page.route("**/api/auth/login", async (route) => {
    const corpo = JSON.parse(route.request().postData() ?? "{}") as { totp?: string };
    tentativas.push(corpo);
    if (!corpo.totp) {
      return route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ erro: { codigo: "totp_necessario", mensagem: "Informe o código do autenticador." } }),
      });
    }
    // O backend real define os cookies; aqui a simulação faz o mesmo.
    await context.addCookies([
      { name: "sinais_sessao", value: "sessao-de-teste", url: BASE },
      { name: "sinais_csrf", value: "csrf-de-teste", url: BASE },
    ]);
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ usuario: usuarioAdmin }) });
  });

  await page.goto("/terminal");
  await expect(page).toHaveURL(/\/login\?proximo=%2Fterminal/);

  await page.getByLabel("E-mail").fill("admin@teste.local");
  await page.getByLabel("Senha").fill("senha-de-teste-123");
  await page.getByRole("button", { name: "Entrar" }).click();

  const codigo = page.getByLabel("Código de verificação");
  await expect(codigo).toBeVisible();
  await codigo.fill("123456");
  await page.getByRole("button", { name: "Verificar" }).click();

  await expect(page).toHaveURL(/\/terminal$/);
  expect(tentativas).toHaveLength(2);
  await expect(page.getByRole("link", { name: "Admin" })).toBeVisible();
});

test("credenciais inválidas mostram a mensagem do servidor", async ({ page }) => {
  await page.route("**/api/auth/login", (route) =>
    route.fulfill({
      status: 401,
      contentType: "application/json",
      body: JSON.stringify({ erro: { codigo: "credenciais_invalidas", mensagem: "E-mail ou senha incorretos." } }),
    }),
  );
  await page.goto("/login");
  await page.getByLabel("E-mail").fill("x@teste.local");
  await page.getByLabel("Senha").fill("errada-123456");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page.getByRole("alert")).toHaveText("E-mail ou senha incorretos.");
});
