import { expect, test } from "@playwright/test";
import { entrarComCookie, simularBackend } from "./mocks";

test("terminal mostra AGUARDAR nas 5 expirações, a análise e o candle ao vivo", async ({ page, context }) => {
  await entrarComCookie(context);
  await simularBackend(page);
  await page.goto("/terminal");

  const tabela = page.getByRole("table", { name: "Sinais por expiração" });
  await expect(tabela.getByRole("row")).toHaveCount(6);
  await expect(tabela.getByText("AGUARDAR")).toHaveCount(5);
  await expect(tabela.getByText("Nenhum modelo validado para esta expiração").first()).toBeVisible();

  await expect(page.getByText("Tendência de alta em 1m e 5m (teste)")).toBeVisible();
  await expect(page.getByTestId("regiao-resistencia")).toContainText("difícil de romper");
  await expect(page.getByLabel("Aviso de risco")).toBeVisible();

  // Candle em formação chegou pelo WebSocket simulado.
  await expect(page.getByTestId("ultimo-fechamento")).toHaveText("43.300,50");
  await expect(page.getByText("Ao vivo")).toBeVisible();
});

test("modo Avançado é salvo nas preferências e mostra os indicadores", async ({ page, context }) => {
  await entrarComCookie(context);
  const patches: unknown[] = [];
  await simularBackend(page, {
    aoChamar: (metodo, caminho, corpo) => {
      if (metodo === "PATCH" && caminho === "/api/eu/preferencias") patches.push(corpo);
    },
  });
  await page.goto("/terminal");
  await expect(page.getByText("Tendência de alta em 1m e 5m (teste)")).toBeVisible();
  await expect(page.getByText("RSI", { exact: true })).toHaveCount(0);

  await page.getByText("Avançado", { exact: true }).click();
  await expect(page.getByText("RSI", { exact: true })).toBeVisible();
  expect(patches).toContainEqual({ modo: "avancado" });
});

test("assinatura vencida (402) leva à tela de assinatura", async ({ page, context }) => {
  await entrarComCookie(context);
  await simularBackend(page, { statusEu: 402 });
  await page.goto("/terminal");
  await expect(page).toHaveURL(/\/assinatura$/);
  await expect(page.getByRole("heading", { name: "Sua assinatura não está ativa" })).toBeVisible();
});

test("tempo gráfico troca a série pedida", async ({ page, context }) => {
  await entrarComCookie(context);
  const pedidos: string[] = [];
  await simularBackend(page, {
    aoChamar: (_m, caminho) => {
      if (caminho === "/api/candles") pedidos.push(caminho);
    },
  });
  const resposta = page.waitForRequest((r) => r.url().includes("/api/candles") && r.url().includes("tg=15m"));
  await page.goto("/terminal");
  await page.getByRole("group", { name: "Tempo gráfico" }).getByRole("button", { name: "15m" }).click();
  await resposta;
  await expect(page.getByRole("group", { name: "Tempo gráfico" }).getByRole("button", { name: "15m" })).toHaveAttribute("aria-pressed", "true");
});
