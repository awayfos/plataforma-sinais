import { beforeEach, describe, expect, it, vi } from "vitest";
import { ErroApi, definirTratadorSessao, requisicao } from "@/lib/api/cliente";
import { simularFetch } from "../apoio/fetch";

const tratador = { aoNaoAutenticado: vi.fn(), aoAssinaturaVencida: vi.fn() };

beforeEach(() => {
  tratador.aoNaoAutenticado = vi.fn();
  tratador.aoAssinaturaVencida = vi.fn();
  definirTratadorSessao(tratador);
  document.cookie = "sinais_csrf=token-123; path=/";
});

describe("requisicao", () => {
  it("envia X-CSRF-Token em mutações", async () => {
    const chamadas = simularFetch(() => ({ corpo: { ok: true } }));
    await requisicao("/api/eu/preferencias", { metodo: "PATCH", corpo: { modo: "avancado" } });
    await requisicao("/api/x", { metodo: "POST" });
    await requisicao("/api/x", { metodo: "PUT", corpo: [] });
    for (const c of chamadas) expect(c.headers["x-csrf-token"]).toBe("token-123");
    expect(chamadas[0]!.corpo).toEqual({ modo: "avancado" });
  });

  it("não envia CSRF em GET", async () => {
    const chamadas = simularFetch(() => ({ corpo: [] }));
    await requisicao("/api/ativos");
    expect(chamadas[0]!.headers["x-csrf-token"]).toBeUndefined();
  });

  it("401 chama aoNaoAutenticado e lança ErroApi com a mensagem do servidor", async () => {
    simularFetch(() => ({ status: 401, corpo: { erro: { codigo: "sem_sessao", mensagem: "Faça login." } } }));
    const erro = await requisicao("/api/eu").catch((e: unknown) => e);
    expect(erro).toBeInstanceOf(ErroApi);
    expect((erro as ErroApi).status).toBe(401);
    expect((erro as ErroApi).codigo).toBe("sem_sessao");
    expect((erro as ErroApi).message).toBe("Faça login.");
    expect(tratador.aoNaoAutenticado).toHaveBeenCalledOnce();
  });

  it("401 com semRedirecionar não chama o tratador", async () => {
    simularFetch(() => ({ status: 401, corpo: { erro: { codigo: "credenciais", mensagem: "x" } } }));
    await expect(requisicao("/api/auth/login", { metodo: "POST", semRedirecionar: true })).rejects.toBeInstanceOf(ErroApi);
    expect(tratador.aoNaoAutenticado).not.toHaveBeenCalled();
  });

  it("402 chama aoAssinaturaVencida", async () => {
    simularFetch(() => ({ status: 402, corpo: { erro: { codigo: "assinatura_vencida", mensagem: "Venceu." } } }));
    await expect(requisicao("/api/sinais?simbolo=BTCUSDT")).rejects.toBeInstanceOf(ErroApi);
    expect(tratador.aoAssinaturaVencida).toHaveBeenCalledOnce();
  });

  it("429 dá a mensagem fixa de limite", async () => {
    simularFetch(() => ({ status: 429, corpo: { erro: { codigo: "limite", mensagem: "rate" } } }));
    await expect(requisicao("/api/ativos")).rejects.toThrow(
      "Muitas requisições. Aguarde alguns segundos e tente de novo.",
    );
  });

  it("erro sem corpo JSON vira mensagem genérica com o status", async () => {
    simularFetch(() => ({ status: 502, texto: "<html>Bad Gateway</html>" }));
    await expect(requisicao("/api/ativos")).rejects.toThrow(/Erro inesperado \(502\)/);
  });

  it("204 devolve undefined", async () => {
    simularFetch(() => ({ status: 204 }));
    await expect(requisicao("/api/auth/logout", { metodo: "POST" })).resolves.toBeUndefined();
  });

  it("registra o relógio do servidor pelo cabeçalho Date", async () => {
    const { agoraServidor, redefinirRelogio } = await import("@/lib/relogio");
    redefinirRelogio();
    const servidor = Date.now() + 60_000;
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("[]", { status: 200, headers: { Date: new Date(servidor).toUTCString() } })),
    );
    await requisicao("/api/ativos");
    expect(Math.abs(agoraServidor(Date.now()) - servidor)).toBeLessThan(2_000);
    redefinirRelogio();
  });

  it("falha de rede vira ErroApi status 0", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("Failed to fetch"); }));
    const erro = (await requisicao("/api/ativos").catch((e: unknown) => e)) as ErroApi;
    expect(erro).toBeInstanceOf(ErroApi);
    expect(erro.status).toBe(0);
  });
});
