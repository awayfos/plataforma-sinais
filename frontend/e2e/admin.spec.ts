import { expect, test } from "@playwright/test";
import { entrarComCookie, simularBackend, usuarioAdmin, usuarioCliente } from "./mocks";

test("admin lista usuários", async ({ page, context }) => {
  await entrarComCookie(context);
  await simularBackend(page, { usuario: usuarioAdmin });
  await page.goto("/admin/usuarios");
  await expect(page.getByRole("heading", { name: "Usuários" })).toBeVisible();
  await expect(page.getByText("ana@teste.local")).toBeVisible();
});

test("cliente não vê a área admin", async ({ page, context }) => {
  await entrarComCookie(context);
  await simularBackend(page, { usuario: usuarioCliente });
  await page.goto("/admin/usuarios");
  await expect(page.getByRole("heading", { name: "Acesso restrito" })).toBeVisible();
});
