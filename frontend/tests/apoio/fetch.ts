// Apoio de TESTE: simula o backend respondendo ao fetch. Nada daqui vai para a aplicação.
import { vi } from "vitest";

export interface Chamada {
  url: string;
  metodo: string;
  corpo: unknown;
  headers: Record<string, string>;
}

export interface RespostaSimulada {
  status?: number;
  corpo?: unknown;
  texto?: string;
}

export function simularFetch(responder: (c: Chamada) => RespostaSimulada | undefined): Chamada[] {
  const chamadas: Chamada[] = [];
  const fn = vi.fn(async (entrada: RequestInfo | URL, init?: RequestInit) => {
    const url = String(entrada);
    const metodo = init?.method ?? "GET";
    const headers = Object.fromEntries(new Headers(init?.headers).entries());
    const corpo = typeof init?.body === "string" ? JSON.parse(init.body) : undefined;
    const chamada = { url, metodo, corpo, headers };
    chamadas.push(chamada);
    const r = responder(chamada) ?? {
      status: 404,
      corpo: { erro: { codigo: "nao_encontrado", mensagem: "Não encontrado" } },
    };
    const status = r.status ?? 200;
    if (status === 204) return new Response(null, { status });
    if (r.texto !== undefined) return new Response(r.texto, { status, headers: { "Content-Type": "text/html" } });
    return new Response(JSON.stringify(r.corpo ?? null), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fn);
  return chamadas;
}

export function caminho(url: string): string {
  return new URL(url, "http://teste.local").pathname;
}
