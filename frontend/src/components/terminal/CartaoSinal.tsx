"use client";

import { api } from "@/lib/api/endpoints";
import type { Sinal } from "@/lib/api/tipos";
import { formatarDuracao, formatarHora, formatarPercentual, formatarPreco } from "@/lib/formato";
import { EXPIRACOES_CURTAS, ROTULO_EXPIRACAO, estadoJanela, estatisticas } from "@/lib/sinais";
import { usarAgora } from "@/lib/usarAgora";
import { usarDados } from "@/lib/usarDados";
import { Dica } from "@/components/ui/Dica";
import { SeloDirecao } from "./Direcao";

const DIAS_HISTORICO = 30;

function HistoricoDoSinal({ simbolo, sinal }: { simbolo: string; sinal: Sinal }) {
  const { dados, erro, carregando } = usarDados(`${simbolo}:${sinal.expiracao}`, (s) => {
    const fim = Date.now();
    return api.historico({ simbolo, inicio: fim - DIAS_HISTORICO * 86_400_000, fim }, s);
  });
  let conteudo: React.ReactNode;
  if (carregando) conteudo = <span className="text-apagado">Carregando…</span>;
  else if (erro) conteudo = <span className="text-apagado">Histórico indisponível agora.</span>;
  else {
    const e = estatisticas((dados ?? []).filter((h) => h.expiracao === sinal.expiracao));
    conteudo =
      e.n === 0 ? (
        <span className="text-apagado">Ainda sem sinais liquidados nesta expiração.</span>
      ) : (
        <span>
          <span className="num text-texto">{formatarPercentual(e.taxa)}</span> de acerto ·{" "}
          <span className="num">n = {e.n}</span> · <span className="num">{e.tie}</span> empates
          {e.apertados > 0 && (
            <>
              {" "}
              · <span className="num">{e.apertados}</span> apertados
            </>
          )}
        </span>
      );
  }
  return (
    <div data-testid="historico-sinal" className="text-[11px] text-suave">
      <span className="text-apagado">Últimos {DIAS_HISTORICO} dias: </span>
      {conteudo}
    </div>
  );
}

export function CartaoSinal({ sinal, simbolo }: { sinal: Sinal; simbolo: string }) {
  const agora = usarAgora(250, sinal.janela_ate !== null);
  const janela = estadoJanela(sinal.janela_ate, agora);
  const curta = EXPIRACOES_CURTAS.includes(sinal.expiracao);
  const compra = sinal.direcao === "COMPRA";

  return (
    <article
      aria-live="polite"
      className={`relative overflow-hidden rounded-lg border bg-painel ${
        janela.dentro ? (compra ? "border-alta/50" : "border-baixa/50") : "border-borda"
      }`}
    >
      <span
        aria-hidden="true"
        className={`absolute inset-y-0 left-0 w-1 ${janela.dentro ? (compra ? "bg-alta" : "bg-baixa") : "bg-borda-forte"}`}
      />
      <div className="space-y-3 py-3 pr-4 pl-5">
        <header className="flex items-start justify-between gap-3">
          <h3 className="flex items-center gap-2 text-sm font-semibold">
            <SeloDirecao direcao={sinal.direcao} grande />
            <span className="text-suave">· {ROTULO_EXPIRACAO[sinal.expiracao]}</span>
          </h3>
          {sinal.probabilidade !== null && (
            <p className="text-right">
              <span className="num block text-lg leading-none font-semibold text-texto">
                <span>{formatarPercentual(sinal.probabilidade)}</span>
              </span>
              <span className="num inline-flex items-center text-[11px] text-apagado">
                <span>calibrada · n = {sinal.n_validacao ?? "—"}</span>
                <Dica termo="probabilidade" />
              </span>
            </p>
          )}
        </header>

        <div className={`rounded-md border px-3 py-2 ${janela.dentro ? "border-borda-forte bg-fundo" : "border-baixa/40 bg-baixa/10"}`}>
          {janela.dentro ? (
            <div className="flex items-center justify-between gap-3">
              <p className="flex items-center text-xs text-suave">
                Entre até {sinal.janela_ate !== null ? formatarHora(sinal.janela_ate) : "—"}
                <Dica termo="janela" />
              </p>
              <p className="text-right">
                <span className="text-[10px] tracking-wide text-apagado uppercase">Restam </span>
                <span data-testid="contagem" className="num text-base font-semibold text-texto">
                  {formatarDuracao(janela.restanteMs)}
                </span>
              </p>
            </div>
          ) : (
            <p className="text-sm font-semibold text-baixa">Fora da janela, não entre</p>
          )}
        </div>

        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-xs">
          {sinal.preco_referencia != null && (
            <>
              <dt className="text-apagado">Preço de referência</dt>
              <dd className="num text-right text-texto">{formatarPreco(sinal.preco_referencia)}</dd>
            </>
          )}
          {sinal.tolerancia_preco != null && (
            <>
              <dt className="flex items-center text-apagado">
                <span>Tolerância de preço</span>
                <Dica termo="tolerancia" />
              </dt>
              <dd className="num text-right text-texto">± {formatarPreco(sinal.tolerancia_preco)}</dd>
            </>
          )}
          {sinal.invalidacao && (
            <>
              <dt className="flex items-center text-apagado">
                <span>Invalidação</span>
                <Dica termo="invalidacao" />
              </dt>
              <dd className="text-right text-texto">{sinal.invalidacao}</dd>
            </>
          )}
        </dl>

        <HistoricoDoSinal simbolo={simbolo} sinal={sinal} />

        <p
          data-testid="nota-entrada"
          className={`rounded border px-2.5 py-1.5 text-[11px] leading-snug ${
            curta ? "border-alerta/30 bg-alerta/5 text-alerta" : "border-borda text-apagado"
          }`}
        >
          {curta
            ? "Expiração curta: exige entrada precisa, no tempo e no preço. Poucos segundos de atraso ou uma diferença pequena de preço na corretora mudam o resultado."
            : "Entre só dentro da janela de entrada. Fora dela o vencimento muda e o sinal deixa de valer."}
        </p>
      </div>
    </article>
  );
}
