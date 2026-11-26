import { expect, test, type WebSocket } from "@playwright/test";
import { codigoTotp } from "./totp";

// Prova o caminho inteiro sem simulação: navegador → Next (rewrite de /api e do WebSocket) → API FastAPI →
// Redis (Pub/Sub ticks:* e streams) → processos coletor/ticks/motor_analise → Binance.
const EMAIL = process.env.SINAIS_E2E_EMAIL ?? "";
const SENHA = process.env.SINAIS_E2E_SENHA ?? "";
const SEGREDO = process.env.SINAIS_E2E_TOTP ?? "";

interface Quadro {
  canal?: string;
  dados?: { t?: number; c?: string; v?: string; fechado?: boolean };
}

test.skip(!EMAIL || !SENHA || !SEGREDO, "defina SINAIS_E2E_EMAIL, SINAIS_E2E_SENHA e SINAIS_E2E_TOTP");

test("admin entra com 2FA e o terminal mostra candles reais que andam tick a tick pelo WebSocket via Next", async ({ page }) => {
  const sockets: WebSocket[] = [];
  const fechamentos: (number | undefined)[] = [];
  const quadros: Quadro[] = [];
  page.on("websocket", (ws) => {
    sockets.push(ws);
    ws.on("close", () => fechamentos.push(undefined));
    ws.on("framereceived", ({ payload }) => {
      if (typeof payload !== "string") return;
      try {
        quadros.push(JSON.parse(payload) as Quadro);
      } catch {
        /* quadro não JSON: ignorado */
      }
    });
  });

  // Login real: senha, depois o código do autenticador calculado aqui.
  await page.goto("/terminal");
  await expect(page).toHaveURL(/\/login/);
  await page.getByLabel("E-mail").fill(EMAIL);
  await page.getByLabel("Senha").fill(SENHA);
  await page.getByRole("button", { name: "Entrar" }).click();
  const campoCodigo = page.getByLabel("Código de verificação");
  await expect(campoCodigo).toBeVisible();
  await campoCodigo.fill(codigoTotp(SEGREDO));
  await page.getByRole("button", { name: "Verificar" }).click();
  await expect(page).toHaveURL(/\/terminal$/, { timeout: 30_000 });

  // Candles do banco (REST via rewrite do Next).
  const grafico = page.getByTestId("grafico");
  await expect.poll(async () => Number((await grafico.getAttribute("data-barras")) ?? 0), { timeout: 60_000 }).toBeGreaterThan(10);

  // WebSocket pelo próprio host do Next (rewrite), conectado e sem laço de reconexão (1006).
  const estadoWs = page.locator("header").getByRole("status");
  await expect(estadoWs).toHaveText("Ao vivo", { timeout: 30_000 });
  expect(sockets.length).toBeGreaterThan(0);
  const url = new URL(sockets[0]!.url());
  expect(`${url.protocol}//${url.host}${url.pathname}`).toBe(`ws://${new URL(page.url()).host}/api/ws`);

  // A barra em formação muda com ticks reais em até 20 s.
  const emFormacao = () => quadros.filter((q) => q.canal?.startsWith("candles:") && q.dados?.fechado === false);
  const inicio = emFormacao().length;
  await expect
    .poll(() => new Set(emFormacao().slice(inicio).map((q) => `${q.dados?.t}:${q.dados?.c}:${q.dados?.v}`)).size, {
      timeout: 20_000,
      intervals: [250],
    })
    .toBeGreaterThan(1);
  // ... e o gráfico mostra o último valor que chegou.
  await expect
    .poll(async () => (await grafico.getAttribute("data-ultimo-fechamento")) === emFormacao().at(-1)?.dados?.c, {
      timeout: 10_000,
    })
    .toBe(true);

  // Painel de análise: análise real ou o estado "análise indisponível" (o motor publica no próximo 1m fechado).
  const painel = page.locator("section[aria-labelledby='t-analise']");
  await expect(
    painel.getByTestId("minuto-analise").or(painel.getByText("Análise ainda não disponível para este ativo.")),
  ).toBeVisible({ timeout: 30_000 });

  // Sem laço de reconexão: a mesma conexão continua aberta.
  await page.waitForTimeout(5_000);
  expect(sockets.length).toBe(1);
  expect(fechamentos).toHaveLength(0);
  await expect(estadoWs).toHaveText("Ao vivo");
});
