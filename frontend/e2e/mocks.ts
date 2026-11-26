// SIMULAÇÃO DE TESTE: backend falso para os testes ponta a ponta (Playwright).
// Nenhum destes dados aparece na aplicação real; eles só existem durante os testes.
import type { BrowserContext, Page, Route } from "@playwright/test";

export const BASE = "http://127.0.0.1:3100";

export const usuarioCliente = {
  id: 1,
  email: "cliente@teste.local",
  nome: "Cliente de Teste",
  papel: "cliente",
  modo: "essencial",
  assinatura: { plano: "Mensal (teste)", status: "ativa", vence_em: Date.now() + 20 * 86_400_000 },
};

export const usuarioAdmin = { ...usuarioCliente, id: 2, email: "admin@teste.local", nome: "Admin de Teste", papel: "admin" };

const MOTIVO = "Nenhum modelo validado para esta expiração";
export const sinaisAguardar = ["1m", "5m", "15m", "30m", "60m"].map((expiracao) => ({
  expiracao,
  direcao: "AGUARDAR",
  probabilidade: null,
  n_validacao: null,
  motivo: MOTIVO,
  janela_ate: null,
  invalidacao: null,
  modelo: null,
}));

export function candlesTeste(n = 120) {
  const ultimo = Math.floor(Date.now() / 60_000) * 60_000 - 60_000;
  return Array.from({ length: n }, (_, i) => {
    const base = 43_000 + Math.round(Math.sin(i / 7) * 120);
    return {
      t: ultimo - (n - 1 - i) * 60_000,
      o: `${base}.00`,
      h: `${base + 25}.00`,
      l: `${base - 25}.00`,
      c: `${base + (i % 2 ? 10 : -10)}.00`,
      v: "12.5",
    };
  });
}

export const analiseTeste = {
  simbolo: "BTCUSDT",
  t: Date.now() - 60_000,
  preco: 43_120.5,
  tendencia: { "1m": 1, "5m": 1, "15m": 0, "1h": -1 },
  forca_tendencia: 27.4,
  regioes: {
    resistencia: { preco: 43_400, distancia_atr: 0.4, toques: 5 },
    suporte: { preco: 43_010, distancia_atr: 1.2, toques: 2 },
  },
  estrutura: { ultimo_evento: "BOS_ALTA", topo: 43_380, fundo: 42_900 },
  volume: { relativo: 1.8, pressao_compradora: 0.62 },
  indicadores: { rsi: 61.2, macd_hist: 4.1, estoc_k: 78, bb_pct: 0.81, atr: 38.5 },
  price_action: { impulso: 0.7, desaceleracao: 0.2, lateral: false },
  resumo: ["Tendência de alta em 1m e 5m (teste)", "Preço a 0,4 ATR de uma resistência tocada 5 vezes (teste)"],
};

export const usuariosAdmin = [
  { id: 7, email: "ana@teste.local", nome: "Ana Souza", papel: "cliente", status: "ativo", assinatura: { plano: "Mensal", status: "ativa", vence_em: Date.now() + 86_400_000 } },
];

export async function entrarComCookie(context: BrowserContext) {
  await context.addCookies([
    { name: "sinais_sessao", value: "sessao-de-teste", url: BASE },
    { name: "sinais_csrf", value: "csrf-de-teste", url: BASE },
  ]);
}

export interface OpcoesBackend {
  usuario?: Record<string, unknown>;
  /** Ticks do candle em formação enviados a cada 100 ms após o snapshot (todos no mesmo t). */
  ticks?: number;
  statusEu?: number;
  aoChamar?: (metodo: string, caminho: string, corpo: unknown) => void;
}

function json(route: Route, status: number, corpo: unknown) {
  return route.fulfill({ status, contentType: "application/json", body: JSON.stringify(corpo) });
}

export async function simularBackend(page: Page, opcoes: OpcoesBackend = {}) {
  let usuario = { ...(opcoes.usuario ?? usuarioCliente) };
  const candles = candlesTeste();

  await page.route("**/api/**", async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const caminho = url.pathname;
    const metodo = req.method();
    const corpo = req.postData() ? JSON.parse(req.postData()!) : undefined;
    opcoes.aoChamar?.(metodo, caminho, corpo);

    if (opcoes.statusEu && caminho !== "/api/auth/logout") {
      return json(route, opcoes.statusEu, { erro: { codigo: "assinatura_vencida", mensagem: "Sua assinatura venceu." } });
    }
    switch (caminho) {
      case "/api/eu":
        return json(route, 200, usuario);
      case "/api/eu/preferencias":
        usuario = { ...usuario, ...(corpo?.modo ? { modo: corpo.modo } : {}) };
        return json(route, 200, usuario);
      case "/api/auth/logout":
        return route.fulfill({ status: 204 });
      case "/api/ativos":
        return json(route, 200, [
          { simbolo: "BTCUSDT", nome: "Bitcoin", classe: "cripto", aberto: true },
          { simbolo: "ETHUSDT", nome: "Ethereum", classe: "cripto", aberto: true },
        ]);
      case "/api/candles":
        return json(route, 200, candles);
      case "/api/analise":
        return json(route, 200, { ...analiseTeste, simbolo: url.searchParams.get("simbolo") });
      case "/api/sinais":
        return json(route, 200, sinaisAguardar);
      case "/api/sinais/historico":
        return json(route, 200, []);
      case "/api/admin/usuarios":
        return json(route, 200, usuariosAdmin);
      case "/api/admin/planos":
        return json(route, 200, []);
      default:
        return json(route, 404, { erro: { codigo: "nao_encontrado", mensagem: `Rota simulada ausente: ${caminho}` } });
    }
  });

  await page.routeWebSocket(/\/api\/ws$/, (ws) => {
    ws.onMessage((mensagem) => {
      const msg = JSON.parse(String(mensagem)) as { acao: string; canal: string };
      if (msg.acao === "assinar" && msg.canal.startsWith("candles:")) {
        const t = candles.at(-1)!.t + 60_000;
        // Snapshot imediato do candle em formação.
        ws.send(
          JSON.stringify({
            canal: msg.canal,
            dados: { t, o: "43300.00", h: "43320.00", l: "43290.00", c: "43300.50", v: "3.2", fechado: false },
          }),
        );
        let i = 0;
        const total = opcoes.ticks ?? 0;
        if (total > 0) {
          const id = setInterval(() => {
            i += 1;
            const c = (43300 + i * 0.5).toFixed(2);
            ws.send(
              JSON.stringify({
                canal: msg.canal,
                dados: { t, o: "43300.00", h: (43320 + i * 0.5).toFixed(2), l: "43290.00", c, v: (3.2 + i * 0.1).toFixed(1), fechado: false },
              }),
            );
            if (i >= total) clearInterval(id);
          }, 100);
        }
      }
    });
  });

  return candles;
}
