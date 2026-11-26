import { defineConfig, devices } from "@playwright/test";

// Ponta a ponta REAL (job e2e-real do CI): navegador → Next (next start) → API → Redis → Binance.
// Nada é simulado: o backend sobe pelo Docker Compose e os ticks vêm da Binance.
// Usa http://localhost (não 127.0.0.1): é a origem aceita pelo backend e o host dos cookies.
const porta = Number(process.env.SINAIS_E2E_PORTA ?? 3100);

export default defineConfig({
  testDir: "./e2e-real",
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: 0, // o código TOTP não pode ser reutilizado (o backend recusa o mesmo passo duas vezes)
  timeout: 180_000,
  reporter: process.env.CI ? [["list"], ["html", { open: "never", outputFolder: "playwright-report-real" }]] : "list",
  use: {
    baseURL: `http://localhost:${porta}`,
    trace: "retain-on-failure",
    locale: "pt-BR",
    timezoneId: "America/Sao_Paulo",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: `npm run start -- -p ${porta}`,
    url: `http://localhost:${porta}/login`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
