import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Historico } from "@/components/historico/Historico";
import { TabelaHistorico } from "@/components/historico/TabelaHistorico";
import type { SinalHistorico } from "@/lib/api/tipos";
import { caminho, simularFetch } from "../apoio/fetch";

const itens: SinalHistorico[] = [
  { id: "1", simbolo: "BTCUSDT", expiracao: "1m", direcao: "COMPRA", gerado_em: Date.parse("2026-11-25T13:30:00Z"), preco_referencia: "43250.10000000", resultado: "WIN", apertado: true },
  { id: "2", simbolo: "BTCUSDT", expiracao: "5m", direcao: "VENDA", gerado_em: Date.parse("2026-11-25T13:35:00Z"), preco_referencia: "43200.00", resultado: "LOSS", apertado: false },
  { id: "3", simbolo: "ETHUSDT", expiracao: "15m", direcao: "COMPRA", gerado_em: Date.parse("2026-11-25T13:45:00Z"), preco_referencia: "2300.5", resultado: "TIE", apertado: false },
  { id: "4", simbolo: "ETHUSDT", expiracao: "15m", direcao: "COMPRA", gerado_em: Date.parse("2026-11-25T14:00:00Z"), preco_referencia: "2301", resultado: "SEM_DADO", apertado: null },
];

describe("TabelaHistorico", () => {
  it("lista com resultado, preço e marca de apertado", () => {
    render(<TabelaHistorico itens={itens} />);
    const linhas = screen.getAllByRole("row").slice(1);
    expect(linhas).toHaveLength(4);
    expect(linhas[0]).toHaveTextContent("WIN");
    expect(linhas[0]).toHaveTextContent("43.250,10");
    expect(linhas[0]).toHaveTextContent("Apertado");
    expect(linhas[1]).not.toHaveTextContent("Apertado");
    expect(linhas[3]).toHaveTextContent("Sem dado");
  });
});

describe("Historico", () => {
  it("resume a taxa (sem empates e sem dado) e filtra pelo ativo", async () => {
    const chamadas = simularFetch((c) => {
      if (caminho(c.url) === "/api/ativos") return { corpo: [{ simbolo: "BTCUSDT", nome: "Bitcoin", classe: "cripto", aberto: true }] };
      if (caminho(c.url) === "/api/sinais/historico") return { corpo: itens };
      return undefined;
    });
    const user = userEvent.setup();
    render(<Historico />);
    expect(await screen.findByTestId("resumo-taxa")).toHaveTextContent("50,0%");
    // "Todos": sem simbolo na consulta (o backend devolve todos os ativos do plano)
    const primeira = chamadas.find((c) => caminho(c.url) === "/api/sinais/historico")!;
    expect(new URL(primeira.url, "http://x").searchParams.has("simbolo")).toBe(false);
    await user.selectOptions(screen.getByLabelText("Ativo"), "BTCUSDT");
    await vi.waitFor(() => {
      const ultima = chamadas.filter((c) => caminho(c.url) === "/api/sinais/historico").at(-1)!;
      const q = new URL(ultima.url, "http://x").searchParams;
      expect(q.get("simbolo")).toBe("BTCUSDT");
      expect(Number(q.get("inicio"))).toBeGreaterThan(0);
      expect(Number(q.get("fim"))).toBeGreaterThan(Number(q.get("inicio")));
    });
  });

  it("não lista AGUARDAR e pagina de 50 em 50", async () => {
    const muitos: SinalHistorico[] = Array.from({ length: 120 }, (_, i) => ({
      ...itens[1]!,
      id: `m${i}`,
      gerado_em: Date.parse("2026-11-25T00:00:00Z") + i * 60_000,
    }));
    const espera: SinalHistorico = { ...itens[0]!, id: "espera", direcao: "AGUARDAR", resultado: null, apertado: null };
    simularFetch((c) => {
      if (caminho(c.url) === "/api/ativos") return { corpo: [] };
      if (caminho(c.url) === "/api/sinais/historico") return { corpo: [espera, ...muitos] };
      return undefined;
    });
    const user = userEvent.setup();
    render(<Historico />);
    expect(await screen.findByTestId("resumo-n")).toHaveTextContent("120");
    expect(screen.getAllByRole("row").slice(1)).toHaveLength(50);
    expect(screen.queryByText("AGUARDAR")).toBeNull();
    await user.click(screen.getByRole("button", { name: /Mostrar mais/ }));
    expect(screen.getAllByRole("row").slice(1)).toHaveLength(100);
  });

  it("sem sinais mostra estado vazio explicativo", async () => {
    simularFetch((c) => {
      if (caminho(c.url) === "/api/ativos") return { corpo: [] };
      if (caminho(c.url) === "/api/sinais/historico") return { corpo: [] };
      return undefined;
    });
    render(<Historico />);
    expect(await screen.findByText(/Nenhum sinal emitido no período/)).toBeInTheDocument();
  });
});
