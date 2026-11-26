import type { Resultado, SinalHistorico } from "@/lib/api/tipos";
import { formatarDataHora, formatarPreco } from "@/lib/formato";
import { ROTULO_EXPIRACAO } from "@/lib/sinais";
import { Dica } from "@/components/ui/Dica";
import { tabela } from "@/components/ui/estilos";
import { SeloDirecao } from "@/components/terminal/Direcao";

const RESULTADO: Record<Resultado, { texto: string; classe: string }> = {
  WIN: { texto: "WIN", classe: "text-alta" },
  LOSS: { texto: "LOSS", classe: "text-baixa" },
  TIE: { texto: "Empate", classe: "text-neutro" },
  SEM_DADO: { texto: "Sem dado", classe: "text-apagado" },
};

export function TabelaHistorico({ itens }: { itens: SinalHistorico[] }) {
  return (
    <div className="overflow-x-auto">
      <table className={tabela.raiz}>
        <caption className="sr-only">Sinais emitidos e resultados</caption>
        <thead className={tabela.cabeca}>
          <tr>
            <th scope="col" className={tabela.th}>Data e hora</th>
            <th scope="col" className={tabela.th}>Ativo</th>
            <th scope="col" className={tabela.th}>Expiração</th>
            <th scope="col" className={tabela.th}>Sinal</th>
            <th scope="col" className={`${tabela.th} text-right`}>Preço de referência</th>
            <th scope="col" className={tabela.th}>Resultado</th>
            <th scope="col" className={tabela.th}>
              Observação
              <Dica termo="apertado" />
            </th>
          </tr>
        </thead>
        <tbody>
          {itens.map((h) => {
            const r = h.resultado ? RESULTADO[h.resultado] : null;
            return (
              <tr key={h.id} className={tabela.linha}>
                <td className={`${tabela.td} num text-[13px] text-suave`}>{formatarDataHora(h.gerado_em)}</td>
                <td className={`${tabela.td} num text-[13px]`}>{h.simbolo}</td>
                <td className={`${tabela.td} text-[13px] text-suave`}>{ROTULO_EXPIRACAO[h.expiracao] ?? h.expiracao}</td>
                <td className={tabela.td}>
                  <SeloDirecao direcao={h.direcao} />
                </td>
                <td className={`${tabela.td} num text-right text-[13px]`}>{formatarPreco(h.preco_referencia)}</td>
                <td className={`${tabela.td} text-[13px] font-semibold`}>
                  {r ? <span className={r.classe}>{r.texto}</span> : <span className="text-apagado">Aguardando vencimento</span>}
                </td>
                <td className={`${tabela.td} text-[12px]`}>
                  {h.apertado ? (
                    <span className="rounded border border-alerta/40 bg-alerta/10 px-1.5 py-0.5 text-[11px] font-medium text-alerta">Apertado</span>
                  ) : null}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
