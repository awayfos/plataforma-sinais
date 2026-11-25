// Capturas de tela para revisão visual (dados de SIMULAÇÃO DE TESTE). Salvas em capturas/ e publicadas pelo CI.
import { expect, test } from "@playwright/test";
import { entrarComCookie, simularBackend, usuarioAdmin } from "./mocks";

test.use({ viewport: { width: 1440, height: 900 } });

test("capturas das telas principais", async ({ page, context }) => {
  await entrarComCookie(context);
  await simularBackend(page, { usuario: { ...usuarioAdmin, modo: "avancado" } });

  await page.goto("/terminal");
  await expect(page.getByTestId("ultimo-fechamento")).toHaveText("43.300,50");
  await page.waitForTimeout(500);
  await page.screenshot({ path: "capturas/terminal-avancado.jpg", type: "jpeg", quality: 70 });

  await page.getByText("Essencial", { exact: true }).click();
  await page.waitForTimeout(300);
  await page.screenshot({ path: "capturas/terminal-essencial.jpg", type: "jpeg", quality: 70 });

  await page.goto("/historico");
  await expect(page.getByText(/Nenhum sinal emitido no período/)).toBeVisible();
  await page.screenshot({ path: "capturas/historico.jpg", type: "jpeg", quality: 70 });

  await page.goto("/perfil");
  await expect(page.getByRole("heading", { name: "Perfil" })).toBeVisible();
  await page.screenshot({ path: "capturas/perfil.jpg", type: "jpeg", quality: 70, fullPage: true });

  await page.goto("/admin/usuarios");
  await expect(page.getByText("ana@teste.local")).toBeVisible();
  await page.screenshot({ path: "capturas/admin-usuarios.jpg", type: "jpeg", quality: 70 });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/terminal");
  await expect(page.getByTestId("ultimo-fechamento")).toHaveText("43.300,50");
  await page.screenshot({ path: "capturas/terminal-celular.jpg", type: "jpeg", quality: 70, fullPage: true });
});

test("captura do login", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/login");
  await page.screenshot({ path: "capturas/login.jpg", type: "jpeg", quality: 70 });
});
