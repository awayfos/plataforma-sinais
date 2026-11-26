import { expect, test } from "@playwright/test";
import { candlesTeste, entrarComCookie, simularBackend } from "./mocks";

test("gráfico anda tick a tick: 50 ticks em 5 s no mesmo t atualizam a última barra sem criar barras", async ({ page, context }) => {
  await entrarComCookie(context);
  await simularBackend(page, { ticks: 50 });
  await page.goto("/terminal");

  const grafico = page.getByTestId("grafico");
  const barrasEsperadas = String(candlesTeste().length + 1); // histórico + 1 barra em formação
  await expect(grafico).toHaveAttribute("data-barras", barrasEsperadas);

  // Amostra a contagem de barras enquanto os ticks chegam.
  const amostras: string[] = [];
  for (let i = 0; i < 10; i++) {
    amostras.push((await grafico.getAttribute("data-barras")) ?? "");
    await page.waitForTimeout(250);
  }
  expect(new Set(amostras)).toEqual(new Set([barrasEsperadas]));

  // Fechamento da última barra = último tick (43300 + 50 × 0,5).
  await expect(grafico).toHaveAttribute("data-ultimo-fechamento", "43325.00", { timeout: 10_000 });
  await expect(grafico).toHaveAttribute("data-barras", barrasEsperadas);
  await expect(page.getByTestId("ultimo-fechamento")).toHaveText("43.325,00");
  await expect(page.getByTestId("preco-BTCUSDT").first()).toHaveText("43.325,00");
});
