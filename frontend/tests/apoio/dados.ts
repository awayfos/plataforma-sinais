// Dados FICTÍCIOS só para testes automatizados (rotulados; nunca exibidos na aplicação).
import type { Analise, Sinal, Usuario } from "@/lib/api/tipos";

export const usuarioTeste: Usuario = {
  id: 1,
  email: "cliente@teste.local",
  nome: "Cliente de Teste",
  papel: "cliente",
  modo: "essencial",
  assinatura: { plano: "Mensal", status: "ativa", vence_em: Date.parse("2026-12-25T03:00:00Z") },
};

export const analiseTeste: Analise = {
  simbolo: "BTCUSDT",
  t: Date.parse("2026-11-25T13:30:00Z"),
  preco: 43250.5,
  tendencia: { "1m": 1, "5m": 1, "15m": 0, "1h": -1 },
  forca_tendencia: 27.4,
  regioes: {
    resistencia: { preco: 43400, distancia_atr: 0.4, toques: 5 },
    suporte: { preco: 43010, distancia_atr: 1.2, toques: 2 },
  },
  estrutura: { ultimo_evento: "BOS_ALTA", topo: 43380, fundo: 42900 },
  volume: { relativo: 1.8, pressao_compradora: 0.62 },
  indicadores: { rsi: 61.2, macd_hist: 4.1, estoc_k: 78, bb_pct: 0.81, atr: 38.5 },
  price_action: { impulso: 0.7, desaceleracao: 0.2, lateral: false },
  resumo: ["Tendência de alta em 1m e 5m", "Preço a 0,4 ATR de uma resistência tocada 5 vezes"],
};

export function aguardar(expiracao: Sinal["expiracao"]): Sinal {
  return {
    expiracao,
    direcao: "AGUARDAR",
    probabilidade: null,
    n_validacao: null,
    motivo: "Nenhum modelo validado para esta expiração",
    janela_ate: null,
    invalidacao: null,
    modelo: null,
  };
}
