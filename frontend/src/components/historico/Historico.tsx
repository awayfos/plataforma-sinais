"use client";

import { useState } from "react";
import { api } from "@/lib/api/endpoints";
import { EXPIRACOES, type Expiracao } from "@/lib/api/tipos";
import { formatarPercentual, periodoAteAgora } from "@/lib/formato";
import { ROTULO_EXPIRACAO, estatisticas } from "@/lib/sinais";
import { useDados } from "@/lib/useDados";
import { Dica } from "@/components/ui/Dica";
import { Carregando, ErroEstado, Vazio } from "@/components/ui/Estado";
import { campoBase, painel, rotulo, tituloPainel } from "@/components/ui/estilos";
import { TabelaHistorico } from "./TabelaHistorico";

const PERIODOS = [
  { dias: 1, rotulo: "Últimas 24 h" },
  { dias: 7, rotulo: "7 dias" },
  { dias: 30, rotulo: "30 dias" },
  { dias: 90, rotulo: "90 dias" },
];

export function Historico() {
  const [simbolo, setSimbolo] = useState("");
  const [dias, setDias] = useState(30);
  const [expiracao, setExpiracao] = useState<Expiracao | "">("");

  const ativos = useDados("ativos", (s) => api.ativos(s));
  const historico = useDados(`historico:${simbolo}:${dias}`, (s) =>
    api.historico({ simbolo: simbolo || undefined, ...periodoAteAgora(dias) }, s),
  );

  const itens = (historico.dados ?? [])
    .filter((h) => !expiracao || h.expiracao === expiracao)
    .sort((a, b) => b.gerado_em - a.gerado_em);
  const resumo = estatisticas(itens);

  return (
    <main className="mx-auto w-full max-w-6xl space-y-4 px-4 py-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Histórico de sinais</h1>
          <p className="mt-1 max-w-2xl text-xs leading-relaxed text-apagado">
            Todos os sinais emitidos, liquidados automaticamente pela fonte de referência, incluindo as derrotas. Empates
            devolvem o valor e ficam fora da taxa de acerto; “sem dado” fica de fora das estatísticas.
          </p>
        </div>
        <form className="flex flex-wrap gap-3" onSubmit={(e) => e.preventDefault()} aria-label="Filtros do histórico">
          <div>
            <label htmlFor="f-ativo" className={rotulo}>Ativo</label>
            <select id="f-ativo" value={simbolo} onChange={(e) => setSimbolo(e.target.value)} className={`${campoBase} w-36 py-1.5`}>
              <option value="">Todos</option>
              {(ativos.dados ?? []).map((a) => (
                <option key={a.simbolo} value={a.simbolo}>{a.simbolo}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="f-expiracao" className={rotulo}>Expiração</label>
            <select
              id="f-expiracao"
              value={expiracao}
              onChange={(e) => setExpiracao(e.target.value as Expiracao | "")}
              className={`${campoBase} w-28 py-1.5`}
            >
              <option value="">Todas</option>
              {EXPIRACOES.map((x) => (
                <option key={x} value={x}>{ROTULO_EXPIRACAO[x]}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="f-periodo" className={rotulo}>Período</label>
            <select id="f-periodo" value={dias} onChange={(e) => setDias(Number(e.target.value))} className={`${campoBase} w-36 py-1.5`}>
              {PERIODOS.map((p) => (
                <option key={p.dias} value={p.dias}>{p.rotulo}</option>
              ))}
            </select>
          </div>
        </form>
      </div>

      <section className="grid grid-cols-2 gap-3 sm:grid-cols-5" aria-label="Resumo do período">
        {(
          [
            ["Liquidados", String(resumo.n), "resumo-n"],
            ["Taxa de acerto", formatarPercentual(resumo.taxa), "resumo-taxa"],
            ["WIN / LOSS", `${resumo.win} / ${resumo.loss}`, "resumo-wl"],
            ["Empates", String(resumo.tie), "resumo-tie"],
            ["Apertados", String(resumo.apertados), "resumo-apertados"],
          ] as const
        ).map(([nome, valor, id]) => (
          <div key={id} className={`${painel} px-4 py-3`}>
            <p className={tituloPainel}>
              {nome}
              {id === "resumo-apertados" && <Dica termo="apertado" />}
            </p>
            <p data-testid={id} className="num mt-1 text-xl font-semibold">{historico.dados ? valor : "—"}</p>
          </div>
        ))}
      </section>

      <section className={`${painel} p-2`}>
        {historico.carregando && !historico.dados ? (
          <Carregando rotulo="Carregando histórico…" linhas={5} />
        ) : historico.erro ? (
          <ErroEstado mensagem={historico.erro.message} aoTentarDeNovo={historico.recarregar} />
        ) : itens.length === 0 ? (
          <Vazio titulo="Nenhum sinal emitido no período">
            A plataforma só emite COMPRA ou VENDA nas combinações aprovadas na validação estatística. Enquanto nenhuma
            estiver aprovada, todas as expirações ficam em AGUARDAR e o histórico fica vazio.
          </Vazio>
        ) : (
          <TabelaHistorico itens={itens} />
        )}
        {resumo.semDado > 0 && (
          <p className="px-3 py-2 text-[11px] text-apagado">{resumo.semDado} sinal(is) sem dado de liquidação, fora das estatísticas.</p>
        )}
      </section>
    </main>
  );
}
