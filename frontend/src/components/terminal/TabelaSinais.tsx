"use client";

import type { Expiracao, Sinal } from "@/lib/api/tipos";
import { formatarPercentual } from "@/lib/formato";
import { ROTULO_EXPIRACAO, ordenarSinais } from "@/lib/sinais";
import { Dica } from "@/components/ui/Dica";
import { Carregando } from "@/components/ui/Estado";
import { SeloDirecao } from "./Direcao";

export function TabelaSinais({
  sinais,
  selecionada,
  aoSelecionar,
}: {
  sinais: Sinal[] | null;
  selecionada?: Expiracao | null;
  aoSelecionar?: (e: Expiracao) => void;
}) {
  if (!sinais) return <Carregando rotulo="Carregando sinais…" linhas={5} />;
  const linhas = ordenarSinais(sinais);
  const todosAguardar = linhas.every((l) => !l.sinal || l.sinal.direcao === "AGUARDAR");

  return (
    <div>
      <table className="w-full border-collapse text-left text-sm">
        <caption className="sr-only">Sinais por expiração</caption>
        <thead>
          <tr className="border-b border-borda text-[10px] font-semibold tracking-wider text-apagado uppercase">
            <th scope="col" className="py-1.5 pr-2 font-semibold">
              Expiração
              <Dica termo="expiracao" />
            </th>
            <th scope="col" className="py-1.5 pr-2 font-semibold">
              Sinal
            </th>
            <th scope="col" className="py-1.5 pr-2 text-right font-semibold">
              Prob.
              <Dica termo="probabilidade" />
            </th>
            <th scope="col" className="py-1.5 text-right font-semibold">
              Amostra
              <Dica termo="amostra" />
            </th>
          </tr>
        </thead>
        <tbody>
          {linhas.map(({ expiracao, sinal }) => {
            const ativo = sinal && sinal.direcao !== "AGUARDAR";
            return (
              <tr
                key={expiracao}
                onClick={ativo && aoSelecionar ? () => aoSelecionar(expiracao) : undefined}
                className={`border-b border-borda/60 align-top ${ativo ? "cursor-pointer hover:bg-painel-2/60" : ""} ${
                  selecionada === expiracao ? "bg-painel-2/80" : ""
                }`}
              >
                <th scope="row" className="num py-2 pr-2 text-[13px] font-medium text-suave">
                  {ROTULO_EXPIRACAO[expiracao]}
                </th>
                <td className="py-2 pr-2">
                  {sinal ? (
                    <>
                      <SeloDirecao direcao={sinal.direcao} />
                      {sinal.direcao === "AGUARDAR" && sinal.motivo && (
                        <p className="mt-1 text-[11px] leading-snug text-apagado">{sinal.motivo}</p>
                      )}
                    </>
                  ) : (
                    <span className="text-[11px] text-apagado">Sem dados</span>
                  )}
                </td>
                <td className="num py-2 pr-2 text-right text-[13px]">
                  {sinal?.probabilidade != null ? formatarPercentual(sinal.probabilidade) : <span className="text-apagado">—</span>}
                </td>
                <td className="num py-2 text-right text-[12px] text-suave">
                  {sinal?.probabilidade != null && sinal.n_validacao != null ? (
                    `n = ${sinal.n_validacao}`
                  ) : (
                    <span className="text-apagado">—</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {todosAguardar && (
        <p className="mt-3 rounded-md border border-borda bg-fundo/60 px-3 py-2 text-[11px] leading-relaxed text-apagado">
          <span className="font-medium text-suave">AGUARDAR em todas as expirações.</span> Isso é intencional: um sinal só
          aparece quando a combinação ativo × expiração tem vantagem comprovada fora da amostra, acima do equilíbrio do
          payout.
          <Dica termo="aguardar" lado="cima" />
        </p>
      )}
    </div>
  );
}
