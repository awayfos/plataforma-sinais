"use client";

import type { Analise, Direcao3, EventoEstrutura, Modo, Regiao, TempoTendencia } from "@/lib/api/tipos";
import { formatarHora, formatarNumero, formatarPercentual, formatarPreco } from "@/lib/formato";
import type { TermoGlossario } from "@/lib/glossario";
import { Dica } from "@/components/ui/Dica";
import { Carregando, ErroEstado } from "@/components/ui/Estado";
import { tituloPainel } from "@/components/ui/estilos";

/** A partir de quantos toques a região é tratada como "difícil de romper". */
export const TOQUES_DIFICIL = 3;

const TEMPOS: TempoTendencia[] = ["1m", "5m", "15m", "1h"];

const TENDENCIA: Record<`${Direcao3}`, { texto: string; icone: string; cor: string }> = {
  "1": { texto: "Alta", icone: "▲", cor: "text-alta border-alta/30 bg-alta/[0.07]" },
  "0": { texto: "Lateral", icone: "■", cor: "text-neutro border-borda-forte bg-painel-2" },
  "-1": { texto: "Baixa", icone: "▼", cor: "text-baixa border-baixa/30 bg-baixa/[0.07]" },
};

const EVENTO: Record<EventoEstrutura, { texto: string; cor: string }> = {
  BOS_ALTA: { texto: "Rompimento de estrutura para cima (BOS)", cor: "text-alta" },
  BOS_BAIXA: { texto: "Rompimento de estrutura para baixo (BOS)", cor: "text-baixa" },
  CHOCH_ALTA: { texto: "Mudança de caráter para alta (CHoCH)", cor: "text-alta" },
  CHOCH_BAIXA: { texto: "Mudança de caráter para baixa (CHoCH)", cor: "text-baixa" },
};

function Secao({ titulo, termo, children }: { titulo: string; termo?: TermoGlossario; children: React.ReactNode }) {
  return (
    <section className="border-t border-borda px-4 py-3">
      <h3 className={`${tituloPainel} mb-2 flex items-center`}>
        {titulo}
        {termo && <Dica termo={termo} />}
      </h3>
      {children}
    </section>
  );
}

function LinhaRegiao({ tipo, regiao }: { tipo: "resistencia" | "suporte"; regiao: Regiao | null }) {
  const nome = tipo === "resistencia" ? "Resistência" : "Suporte";
  return (
    <div data-testid={`regiao-${tipo}`} className="flex items-start justify-between gap-3 py-1">
      <div>
        <p className="flex items-center text-xs font-medium text-suave">
          <span className={`mr-2 inline-block h-2.5 w-0.5 rounded ${tipo === "resistencia" ? "bg-baixa" : "bg-alta"}`} aria-hidden="true" />
          {nome}
          <Dica termo={tipo} />
        </p>
        {regiao ? (
          <p className="mt-0.5 text-[11px] text-apagado">
            a <span className="num text-suave">{formatarNumero(regiao.distancia_atr, 1)} ATR</span>
            <Dica termo="distancia_atr" /> · {regiao.toques} {regiao.toques === 1 ? "toque" : "toques"}
            {regiao.toques >= TOQUES_DIFICIL && (
              <span className="ml-1.5 rounded border border-ouro/40 bg-ouro/10 px-1 py-px text-[10px] font-semibold text-ouro">
                difícil de romper
              </span>
            )}
          </p>
        ) : (
          <p className="mt-0.5 text-[11px] text-apagado">Nenhuma região próxima</p>
        )}
      </div>
      {regiao && <span className="num text-sm text-texto">{formatarPreco(regiao.preco)}</span>}
    </div>
  );
}

function valorPa(v: number | boolean): { ativo: boolean; texto: string } {
  if (typeof v === "boolean") return { ativo: v, texto: v ? "Sim" : "Não" };
  return { ativo: v >= 0.5, texto: formatarNumero(v, 2) };
}

function Medidor({ fracao, rotulo }: { fracao: number; rotulo: string }) {
  const p = Math.max(0, Math.min(1, fracao));
  return (
    <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-baixa/40" role="img" aria-label={rotulo}>
      <div className="h-full rounded-full bg-alta" style={{ width: `${p * 100}%` }} />
    </div>
  );
}

export function PainelAnalise({
  analise,
  modo,
  aberto,
  carregando = false,
  erro,
  aoTentarDeNovo,
}: {
  analise: Analise | null;
  modo: Modo;
  aberto: boolean;
  carregando?: boolean;
  erro?: string | null;
  aoTentarDeNovo?: () => void;
}) {
  if (!aberto) {
    return (
      <p className="px-4 py-6 text-center text-sm text-apagado">
        Mercado fechado. Fora do horário do ativo não há análise nem sinal.
      </p>
    );
  }
  if (erro) return <div className="p-4"><ErroEstado mensagem={erro} aoTentarDeNovo={aoTentarDeNovo} /></div>;
  if (!analise || carregando) return <div className="p-4"><Carregando rotulo="Carregando análise…" linhas={6} /></div>;

  const avancado = modo === "avancado";
  const pressao = analise.volume.pressao_compradora;
  const pressaoFracao = pressao > 1 ? pressao / 100 : pressao;
  const impulso = valorPa(analise.price_action.impulso);
  const desaceleracao = valorPa(analise.price_action.desaceleracao);

  return (
    <div>
      <div className="flex items-baseline justify-between px-4 pt-3 pb-2">
        <span className="num text-lg font-semibold text-texto">{formatarPreco(analise.preco)}</span>
        <span className="text-[11px] text-apagado">
          Último minuto fechado · <span className="num">{formatarHora(analise.t)}</span>
        </span>
      </div>

      {analise.resumo.length > 0 && (
        <section className="px-4 pb-3" aria-label="Leitura do momento">
          <ul className="space-y-1.5">
            {analise.resumo.map((frase) => (
              <li key={frase} className="flex gap-2 text-[13px] leading-snug text-texto">
                <span className="mt-[7px] size-1 shrink-0 rounded-full bg-ouro" aria-hidden="true" />
                {frase}
              </li>
            ))}
          </ul>
        </section>
      )}

      <Secao titulo="Tendência" termo="tendencia">
        <div className="grid grid-cols-4 gap-1.5">
          {TEMPOS.map((tg) => {
            const t = TENDENCIA[`${analise.tendencia[tg]}`] ?? TENDENCIA["0"];
            return (
              <div key={tg} data-testid={`tendencia-${tg}`} className={`rounded border px-2 py-1.5 text-center ${t.cor}`}>
                <span className="num block text-[10px] text-apagado">{tg}</span>
                <span className="text-xs font-semibold">
                  <span aria-hidden="true" className="mr-1 text-[0.7em]">
                    {t.icone}
                  </span>
                  {t.texto}
                </span>
              </div>
            );
          })}
        </div>
        {avancado && (
          <p className="mt-2 flex items-center text-[11px] text-apagado">
            Força (ADX): <span className="num ml-1 text-suave">{formatarNumero(analise.forca_tendencia, 1)}</span>
            <Dica termo="adx" />
          </p>
        )}
      </Secao>

      <Secao titulo="Regiões">
        <LinhaRegiao tipo="resistencia" regiao={analise.regioes.resistencia} />
        <LinhaRegiao tipo="suporte" regiao={analise.regioes.suporte} />
      </Secao>

      <Secao titulo="Estrutura" termo="estrutura">
        {analise.estrutura.ultimo_evento ? (
          <p className={`text-[13px] font-medium ${EVENTO[analise.estrutura.ultimo_evento].cor}`}>
            {EVENTO[analise.estrutura.ultimo_evento].texto}
          </p>
        ) : (
          <p className="text-[13px] text-apagado">Sem rompimento recente</p>
        )}
        {avancado && (
          <p className="mt-1 text-[11px] text-apagado">
            Topo <span className="num text-suave">{formatarPreco(analise.estrutura.topo)}</span> · Fundo{" "}
            <span className="num text-suave">{formatarPreco(analise.estrutura.fundo)}</span>
          </p>
        )}
      </Secao>

      <Secao titulo="Volume e fluxo">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <p className="flex items-center text-[11px] text-apagado">
              Volume relativo
              <Dica termo="volume_relativo" />
            </p>
            <p className="num text-sm text-texto">{formatarNumero(analise.volume.relativo, 1)}× a média</p>
          </div>
          <div>
            <p className="flex items-center text-[11px] text-apagado">
              Pressão compradora
              <Dica termo="pressao_compradora" />
            </p>
            <p className="num text-sm text-texto">{formatarPercentual(pressaoFracao, 0)}</p>
            <Medidor fracao={pressaoFracao} rotulo={`Compradores ${formatarPercentual(pressaoFracao, 0)} do volume agressor`} />
          </div>
        </div>
      </Secao>

      <Secao titulo="Price action">
        <ul className="flex flex-wrap gap-1.5 text-[11px]">
          <li className={`inline-flex items-center rounded border px-2 py-1 ${impulso.ativo ? "border-info/40 text-info" : "border-borda text-apagado"}`}>
            Impulso{avancado ? `: ${impulso.texto}` : impulso.ativo ? " forte" : " fraco"}
            <Dica termo="impulso" />
          </li>
          <li
            className={`inline-flex items-center rounded border px-2 py-1 ${
              desaceleracao.ativo ? "border-alerta/40 text-alerta" : "border-borda text-apagado"
            }`}
          >
            {desaceleracao.ativo ? "Desacelerando" : "Sem desaceleração"}
            {avancado && typeof analise.price_action.desaceleracao === "number" ? ` (${desaceleracao.texto})` : ""}
            <Dica termo="desaceleracao" />
          </li>
          <li
            className={`inline-flex items-center rounded border px-2 py-1 ${
              analise.price_action.lateral ? "border-alerta/40 text-alerta" : "border-borda text-apagado"
            }`}
          >
            {analise.price_action.lateral ? "Mercado lateral" : "Fora de lateralização"}
            <Dica termo="lateral" />
          </li>
        </ul>
      </Secao>

      {avancado && (
        <Secao titulo="Indicadores">
          <dl className="grid grid-cols-3 gap-x-3 gap-y-2 text-[11px]">
            {(
              [
                ["RSI", "rsi", formatarNumero(analise.indicadores.rsi, 1)],
                ["MACD hist.", "macd", formatarNumero(analise.indicadores.macd_hist, 2)],
                ["Estoc. %K", "estocastico", formatarNumero(analise.indicadores.estoc_k, 1)],
                ["Bollinger %B", "bollinger", formatarNumero(analise.indicadores.bb_pct, 2)],
                ["ATR", "atr", formatarNumero(analise.indicadores.atr, 2)],
              ] as const
            ).map(([nome, termo, valor]) => (
              <div key={nome}>
                <dt className="flex items-center text-apagado">
                  <span>{nome}</span>
                  <Dica termo={termo} />
                </dt>
                <dd className="num text-[13px] text-texto">{valor}</dd>
              </div>
            ))}
          </dl>
        </Secao>
      )}
    </div>
  );
}
