import { describe, expect, it, vi } from "vitest";
import { ClienteTempoReal, atrasoReconexao, type SocketMinimo } from "@/lib/ws/cliente";

class SocketFalso implements SocketMinimo {
  readyState = 0;
  enviados: { acao: string; canal: string }[] = [];
  onopen: (() => void) | null = null;
  onclose: ((ev: { code: number }) => void) | null = null;
  onmessage: ((ev: { data: unknown }) => void) | null = null;
  onerror: (() => void) | null = null;
  send(d: string) { this.enviados.push(JSON.parse(d)); }
  close() { this.readyState = 3; }
  abrir() { this.readyState = 1; this.onopen?.(); }
  cair(code: number) { this.readyState = 3; this.onclose?.({ code }); }
  receber(obj: unknown) { this.onmessage?.({ data: JSON.stringify(obj) }); }
}

function montar(extra: Partial<ConstructorParameters<typeof ClienteTempoReal>[0]> = {}) {
  const sockets: SocketFalso[] = [];
  const agendados: { fn: () => void; ms: number }[] = [];
  const cliente = new ClienteTempoReal({
    url: "ws://teste/api/ws",
    criarSocket: () => { const s = new SocketFalso(); sockets.push(s); return s; },
    agendar: (fn, ms) => { agendados.push({ fn, ms }); },
    aleatorio: () => 1,
    ...extra,
  });
  return { cliente, sockets, agendados };
}

describe("atrasoReconexao", () => {
  it("cresce exponencialmente com jitter e teto de 30 s", () => {
    expect(atrasoReconexao(0, () => 1)).toBe(500);
    expect(atrasoReconexao(0, () => 0)).toBe(250);
    expect(atrasoReconexao(1, () => 1)).toBe(1000);
    expect(atrasoReconexao(3, () => 1)).toBe(4000);
    expect(atrasoReconexao(30, () => 1)).toBe(30_000);
  });
});

describe("ClienteTempoReal", () => {
  it("assina o canal quando a conexão abre e entrega só ao ouvinte do canal", () => {
    const { cliente, sockets } = montar();
    const candles = vi.fn();
    const sinais = vi.fn();
    cliente.assinar("candles:BTCUSDT:1m", candles);
    cliente.assinar("sinais:BTCUSDT", sinais);
    expect(sockets).toHaveLength(1);
    sockets[0]!.abrir();
    expect(sockets[0]!.enviados).toEqual([
      { acao: "assinar", canal: "candles:BTCUSDT:1m" },
      { acao: "assinar", canal: "sinais:BTCUSDT" },
    ]);
    sockets[0]!.receber({ canal: "sinais:BTCUSDT", dados: [] });
    expect(sinais).toHaveBeenCalledWith([]);
    expect(candles).not.toHaveBeenCalled();
  });

  it("cancela o canal quando o último ouvinte sai", () => {
    const { cliente, sockets } = montar();
    const sair = cliente.assinar("analise:BTCUSDT", () => {});
    sockets[0]!.abrir();
    sair();
    expect(sockets[0]!.enviados.at(-1)).toEqual({ acao: "cancelar", canal: "analise:BTCUSDT" });
  });

  it("reconecta com atraso após queda e reassina os canais", () => {
    const status: string[] = [];
    const { cliente, sockets, agendados } = montar({ aoMudarStatus: (s) => status.push(s) });
    cliente.assinar("candles:ETHUSDT:5m", () => {});
    sockets[0]!.abrir();
    sockets[0]!.cair(1006);
    expect(agendados).toHaveLength(1);
    expect(agendados[0]!.ms).toBe(500);
    expect(status.at(-1)).toBe("reconectando");
    agendados[0]!.fn();
    expect(sockets).toHaveLength(2);
    sockets[1]!.cair(1006);
    expect(agendados[1]!.ms).toBe(1000);
    agendados[1]!.fn();
    sockets[2]!.abrir();
    expect(sockets[2]!.enviados).toEqual([{ acao: "assinar", canal: "candles:ETHUSDT:5m" }]);
    expect(status.at(-1)).toBe("conectado");
  });

  it("4402 não reconecta e avisa assinatura vencida", () => {
    const aoAssinaturaVencida = vi.fn();
    const { cliente, sockets, agendados } = montar({ aoAssinaturaVencida });
    cliente.assinar("sinais:BTCUSDT", () => {});
    sockets[0]!.abrir();
    sockets[0]!.cair(4402);
    expect(agendados).toHaveLength(0);
    expect(aoAssinaturaVencida).toHaveBeenCalledOnce();
  });

  it("4401 não reconecta e avisa sessão revogada", () => {
    const aoSessaoRevogada = vi.fn();
    const { cliente, sockets, agendados } = montar({ aoSessaoRevogada });
    cliente.assinar("sinais:BTCUSDT", () => {});
    sockets[0]!.abrir();
    sockets[0]!.cair(4401);
    expect(agendados).toHaveLength(0);
    expect(aoSessaoRevogada).toHaveBeenCalledOnce();
  });

  it("após 3 falhas seguidas sem abrir, avisa (para conferir a sessão por HTTP)", () => {
    const aoFalhasSeguidas = vi.fn();
    const { cliente, sockets, agendados } = montar({ aoFalhasSeguidas });
    cliente.assinar("sinais:BTCUSDT", () => {});
    sockets[0]!.cair(1006);
    agendados[0]!.fn();
    sockets[1]!.cair(1006);
    expect(aoFalhasSeguidas).not.toHaveBeenCalled();
    agendados[1]!.fn();
    sockets[2]!.cair(1006);
    expect(aoFalhasSeguidas).toHaveBeenCalledTimes(1);
  });

  it("uma conexão aberta zera a contagem de falhas", () => {
    const aoFalhasSeguidas = vi.fn();
    const { cliente, sockets, agendados } = montar({ aoFalhasSeguidas });
    cliente.assinar("sinais:BTCUSDT", () => {});
    sockets[0]!.cair(1006);
    agendados[0]!.fn();
    sockets[1]!.abrir();
    sockets[1]!.cair(1006);
    agendados[1]!.fn();
    sockets[2]!.cair(1006);
    expect(aoFalhasSeguidas).not.toHaveBeenCalled();
  });

  it("ignora mensagens inválidas", () => {
    const { cliente, sockets } = montar();
    const f = vi.fn();
    cliente.assinar("sinais:BTCUSDT", f);
    sockets[0]!.abrir();
    sockets[0]!.onmessage?.({ data: "não é json" });
    sockets[0]!.receber({ sem: "canal" });
    expect(f).not.toHaveBeenCalled();
  });

  it("fechar encerra sem reconectar; retomar reabre com os canais ativos", () => {
    const { cliente, sockets, agendados } = montar();
    cliente.assinar("sinais:BTCUSDT", () => {});
    sockets[0]!.abrir();
    cliente.fechar();
    sockets[0]!.cair(1000);
    expect(agendados).toHaveLength(0);
    cliente.retomar();
    expect(sockets).toHaveLength(2);
    sockets[1]!.abrir();
    expect(sockets[1]!.enviados).toEqual([{ acao: "assinar", canal: "sinais:BTCUSDT" }]);
  });
});
