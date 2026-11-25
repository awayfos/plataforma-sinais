"use client";

import { TEMPOS_GRAFICOS, type Desenho, type IndicadoresGrafico, type TempoGrafico } from "@/lib/api/tipos";
import { formatarPreco } from "@/lib/formato";
import type { TermoGlossario } from "@/lib/glossario";
import { Dica } from "@/components/ui/Dica";
import type { Ferramenta } from "./Grafico";

const FERRAMENTAS: { valor: Ferramenta; rotulo: string; icone: string }[] = [
  { valor: "cursor", rotulo: "Cursor", icone: "↖" },
  { valor: "linha", rotulo: "Linha horizontal", icone: "—" },
  { valor: "zona", rotulo: "Zona de preço", icone: "▭" },
];

const INDICADORES: { chave: keyof IndicadoresGrafico; rotulo: string; termo: TermoGlossario; painel?: boolean }[] = [
  { chave: "ema", rotulo: "EMA 9 / 21", termo: "ema" },
  { chave: "bollinger", rotulo: "Bollinger (20, 2)", termo: "bollinger" },
  { chave: "vwap", rotulo: "VWAP", termo: "vwap" },
  { chave: "rsi", rotulo: "RSI (14)", termo: "rsi", painel: true },
  { chave: "macd", rotulo: "MACD (12, 26, 9)", termo: "macd", painel: true },
];

const grupo = "flex items-center rounded-md border border-borda bg-fundo p-0.5";
const item = (ativo: boolean) =>
  `rounded px-2 py-1 text-[12px] font-medium transition-colors ${ativo ? "bg-painel-2 text-texto" : "text-apagado hover:text-suave"}`;

export function BarraFerramentas({
  tempo,
  aoMudarTempo,
  ferramenta,
  aoMudarFerramenta,
  indicadores,
  aoMudarIndicador,
  avancado,
  desenhos,
  aoRemoverDesenho,
  aoLimparDesenhos,
  som,
  aoMudarSom,
}: {
  tempo: TempoGrafico;
  aoMudarTempo: (t: TempoGrafico) => void;
  ferramenta: Ferramenta;
  aoMudarFerramenta: (f: Ferramenta) => void;
  indicadores: IndicadoresGrafico;
  aoMudarIndicador: (chave: keyof IndicadoresGrafico, valor: boolean) => void;
  avancado: boolean;
  desenhos: Desenho[];
  aoRemoverDesenho: (id: string) => void;
  aoLimparDesenhos: () => void;
  som: boolean;
  aoMudarSom: (v: boolean) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-borda px-2 py-1.5" role="toolbar" aria-label="Ferramentas do gráfico">
      <div className={grupo} role="group" aria-label="Tempo gráfico">
        {TEMPOS_GRAFICOS.map((t) => (
          <button key={t} type="button" aria-pressed={tempo === t} onClick={() => aoMudarTempo(t)} className={`num ${item(tempo === t)}`}>
            {t}
          </button>
        ))}
      </div>

      <div className={grupo} role="group" aria-label="Ferramentas de desenho">
        {FERRAMENTAS.map((f) => (
          <button
            key={f.valor}
            type="button"
            aria-pressed={ferramenta === f.valor}
            onClick={() => aoMudarFerramenta(f.valor)}
            title={f.rotulo}
            className={item(ferramenta === f.valor)}
          >
            <span aria-hidden="true" className="mr-1">
              {f.icone}
            </span>
            <span className="hidden xl:inline">{f.rotulo}</span>
            <span className="sr-only xl:hidden">{f.rotulo}</span>
          </button>
        ))}
      </div>

      <details className="relative">
        <summary className={`${grupo} cursor-pointer list-none px-2.5 py-1 text-[12px] font-medium text-suave hover:text-texto`}>
          Indicadores
        </summary>
        <div className="absolute top-full left-0 z-40 mt-1 w-60 rounded-md border border-borda-forte bg-painel-2 p-2 shadow-2xl shadow-black/60">
          {INDICADORES.map((i) => {
            const bloqueado = i.painel && !avancado;
            return (
              <label key={i.chave} className={`flex items-center gap-2 rounded px-2 py-1.5 text-[12px] ${bloqueado ? "text-apagado" : "text-suave hover:bg-painel"}`}>
                <input
                  type="checkbox"
                  checked={indicadores[i.chave] && !bloqueado}
                  disabled={bloqueado}
                  onChange={(e) => aoMudarIndicador(i.chave, e.target.checked)}
                  className="accent-[var(--color-ouro)]"
                />
                <span className="flex-1">{i.rotulo}</span>
                <Dica termo={i.termo} />
              </label>
            );
          })}
          {!avancado && <p className="px-2 pt-1 text-[11px] text-apagado">RSI e MACD ficam disponíveis no modo Avançado.</p>}
        </div>
      </details>

      <details className="relative">
        <summary className={`${grupo} cursor-pointer list-none px-2.5 py-1 text-[12px] font-medium text-suave hover:text-texto`}>
          Desenhos <span className="num ml-1 text-apagado">{desenhos.length}</span>
        </summary>
        <div className="absolute top-full left-0 z-40 mt-1 w-64 rounded-md border border-borda-forte bg-painel-2 p-2 shadow-2xl shadow-black/60">
          {desenhos.length === 0 ? (
            <p className="px-2 py-1.5 text-[11px] text-apagado">
              Use “Linha horizontal” ou “Zona de preço” e clique no gráfico. Os desenhos ficam salvos por ativo.
            </p>
          ) : (
            <ul>
              {desenhos.map((d) => (
                <li key={d.id} className="flex items-center justify-between gap-2 rounded px-2 py-1 text-[12px] text-suave">
                  <span className="num">
                    {d.tipo === "linha" ? `Linha ${formatarPreco(d.preco)}` : `Zona ${formatarPreco(d.de)} – ${formatarPreco(d.ate)}`}
                  </span>
                  <button type="button" onClick={() => aoRemoverDesenho(d.id)} className="text-apagado hover:text-baixa" aria-label={`Remover ${d.tipo} ${d.tipo === "linha" ? formatarPreco(d.preco) : formatarPreco(d.de)}`}>
                    ✕
                  </button>
                </li>
              ))}
              <li className="mt-1 border-t border-borda pt-1">
                <button type="button" onClick={aoLimparDesenhos} className="w-full rounded px-2 py-1 text-left text-[12px] text-baixa hover:bg-painel">
                  Remover todos
                </button>
              </li>
            </ul>
          )}
        </div>
      </details>

      <button
        type="button"
        aria-pressed={som}
        onClick={() => aoMudarSom(!som)}
        className={`ml-auto ${grupo} px-2.5 py-1 text-[12px] font-medium ${som ? "text-ouro" : "text-apagado hover:text-suave"}`}
        title="Alerta sonoro quando surgir um sinal"
      >
        Som {som ? "ligado" : "desligado"}
      </button>
    </div>
  );
}
