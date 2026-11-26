import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProvedorSessao } from "@/components/sessao/ProvedorSessao";
import { Terminal } from "@/components/terminal/Terminal";
import type { Sinal } from "@/lib/api/tipos";
import { ProvedorTempoReal } from "@/lib/ws/ProvedorTempoReal";
import { aguardar, analiseTeste, usuarioTeste } from "../apoio/dados";
import { caminho, simularFetch, type Chamada } from "../apoio/fetch";
import { SocketFalso } from "../apoio/socket";

vi.mock("next/navigation", async () => {
  const { roteador } = await import("../apoio/navegacao");
  return { useRouter: () => roteador, usePathname: () => "/terminal" };
});
// O gráfico (canvas) não roda no jsdom; o resto do terminal é real.
vi.mock("@/components/terminal/Grafico", () => ({ Grafico: () => null }));

const compra: Sinal = {
  expiracao: "1m",
  direcao: "COMPRA",
  probabilidade: 0.57,
  n_validacao: 412,
  motivo: "",
  janela_ate: null,
  invalidacao: null,
  modelo: "m1",
};

let sockets: SocketFalso[];
let agendados: (() => void)[];
let chamadas: Chamada[];

beforeEach(() => {
  sockets = [];
  agendados = [];
  chamadas = simularFetch((c) => {
    const p = caminho(c.url);
    const simbolo = new URL(c.url, "http://x").searchParams.get("simbolo") ?? "BTCUSDT";
    if (p === "/api/eu") return { corpo: usuarioTeste };
    if (p === "/api/ativos")
      return {
        corpo: [
          { simbolo: "BTCUSDT", nome: "Bitcoin", classe: "cripto", aberto: true },
          { simbolo: "ETHUSDT", nome: "Ethereum", classe: "cripto", aberto: true },
        ],
      };
    if (p === "/api/candles") return { corpo: [] };
    if (p === "/api/analise") return { corpo: { ...analiseTeste, simbolo } };
    if (p === "/api/sinais") return { corpo: (["1m", "5m", "15m", "30m", "60m"] as const).map(aguardar) };
    if (p === "/api/sinais/historico") return { corpo: [] };
    if (p === "/api/eu/preferencias") return { corpo: usuarioTeste };
    return undefined;
  });
  render(
    <ProvedorSessao>
      <ProvedorTempoReal
        criarSocket={() => {
          const s = new SocketFalso();
          sockets.push(s);
          return s;
        }}
        agendar={(fn) => {
          agendados.push(fn);
        }}
      >
        <Terminal />
      </ProvedorTempoReal>
    </ProvedorSessao>,
  );
});

const quantas = (p: string) => chamadas.filter((c) => caminho(c.url) === p).length;

async function conectar() {
  await screen.findByText(analiseTeste.resumo[0]!);
  await vi.waitFor(() => expect(sockets.length).toBeGreaterThan(0));
  act(() => sockets[0]!.abrir());
}

describe("Terminal com tempo real", () => {
  it("marca os dados como desatualizados na queda e recarrega tudo ao reconectar", async () => {
    await conectar();
    expect(screen.queryByText(/desatualizad/i)).toBeNull();
    const antes = { sinais: quantas("/api/sinais"), analise: quantas("/api/analise"), candles: quantas("/api/candles") };

    act(() => sockets[0]!.cair(1006));
    expect(await screen.findByText(/desatualizad/i)).toBeInTheDocument();

    act(() => agendados[0]!());
    act(() => sockets[1]!.abrir());
    await vi.waitFor(() => {
      expect(quantas("/api/sinais")).toBe(antes.sinais + 1);
      expect(quantas("/api/analise")).toBe(antes.analise + 1);
      expect(quantas("/api/candles")).toBe(antes.candles + 1);
    });
    await vi.waitFor(() => expect(screen.queryByText(/desatualizad/i)).toBeNull());
  });

  it("erro do canal (ativo fora do plano) aparece para o usuário", async () => {
    await conectar();
    act(() =>
      sockets[0]!.receber({ canal: "sinais:BTCUSDT", erro: { codigo: "ativo_nao_incluido", mensagem: "Ativo não incluído no seu plano." } }),
    );
    expect(await screen.findByText("Ativo não incluído no seu plano.")).toBeInTheDocument();
    expect(screen.getAllByText("AGUARDAR")).toHaveLength(5);
  });

  it("handshake recusado com sessão válida: para o laço rápido e avisa que o ao vivo está indisponível", async () => {
    await conectar();
    act(() => sockets[0]!.cair(1006));
    act(() => agendados[0]!());
    act(() => sockets[1]!.cair(1006));
    act(() => agendados[1]!());
    act(() => sockets[2]!.cair(1006));
    // 3 falhas: confere /api/eu (200) e entra no modo lento
    expect(await screen.findByText(/ao vivo indisponível/i)).toBeInTheDocument();
  });

  it("sinais antigos do WebSocket não vencem o REST novo ao voltar para o ativo", async () => {
    const user = userEvent.setup();
    await conectar();
    act(() => sockets[0]!.receber({ canal: "sinais:BTCUSDT", dados: [compra] }));
    expect(await screen.findByRole("heading", { name: /COMPRA/ })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Ethereum/ }));
    await user.click(screen.getByRole("button", { name: /Bitcoin/ }));

    await vi.waitFor(() => expect(screen.getAllByText("AGUARDAR")).toHaveLength(5));
    expect(screen.queryByRole("heading", { name: /COMPRA/ })).toBeNull();
  });
});
