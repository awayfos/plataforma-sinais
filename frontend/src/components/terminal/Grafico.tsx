"use client";

import {
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  HistogramSeries,
  LineSeries,
  LineStyle,
  createChart,
  type IChartApi,
  type IPriceLine,
  type ISeriesApi,
  type MouseEventParams,
  type SeriesType,
  type Time,
  type UTCTimestamp,
} from "lightweight-charts";
import { useEffect, useRef, useState } from "react";
import { AgrupadorQuadros } from "@/lib/agrupador";
import type { Candle, CandleAoVivo, Desenho, IndicadoresGrafico, TempoGrafico } from "@/lib/api/tipos";
import { TEMPOS_DIARIOS, duracaoTempo, legendaVisivel, numero, proximoFechamento, tempoDoGrafico } from "@/lib/candles";
import { formatarContagemVela, formatarPreco } from "@/lib/formato";
import type { CandleNumerico, Serie } from "@/lib/indicadores";
import { IndicadoresIncrementais } from "@/lib/indicadoresIncrementais";
import { publicarPreco } from "@/lib/precos";
import { agoraServidor } from "@/lib/relogio";
import { SerieAoVivo } from "@/lib/serieAoVivo";
import type { Canal } from "@/lib/ws/cliente";
import { useCanal } from "@/lib/ws/ProvedorTempoReal";
import { PrimitivaZonas } from "./primitivaZona";

export type Ferramenta = "cursor" | "linha" | "zona";
type CanalCandles = Extract<Canal, `candles:${string}`>;

const paraTempo = (ms: number, tempo: TempoGrafico) => tempoDoGrafico(ms, tempo) as UTCTimestamp;

const COR = {
  fundo: "#0a0d12",
  grade: "#121821",
  texto: "#7d8798",
  borda: "#1a212c",
  alta: "#26b58c",
  baixa: "#f0616d",
  ouro: "#d6ad5c",
  azul: "#5aa9e6",
  roxo: "#b48cf2",
  cinza: "rgba(163, 172, 186, 0.55)",
};

function novoId(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function linha(serie: Serie, tempos: UTCTimestamp[]) {
  return serie.map((v, i) => (v === null ? { time: tempos[i]! } : { time: tempos[i]!, value: v }));
}

function numerico(k: Candle): CandleNumerico {
  return { t: k.t, h: numero(k.h), l: numero(k.l), c: numero(k.c), v: numero(k.v) };
}

function barra(k: Candle, time: UTCTimestamp) {
  return { time, open: numero(k.o), high: numero(k.h), low: numero(k.l), close: numero(k.c) };
}

function barraVolume(k: Candle, time: UTCTimestamp) {
  return {
    time,
    value: numero(k.v),
    color: numero(k.c) >= numero(k.o) ? "rgba(38, 181, 140, 0.32)" : "rgba(240, 97, 109, 0.32)",
  };
}

function corHist(h: number) {
  return h >= 0 ? "rgba(38, 181, 140, 0.6)" : "rgba(240, 97, 109, 0.6)";
}

interface SeriesIndicadores {
  lista: ISeriesApi<SeriesType>[];
  ema9?: ISeriesApi<"Line">;
  ema21?: ISeriesApi<"Line">;
  bbMedia?: ISeriesApi<"Line">;
  bbSup?: ISeriesApi<"Line">;
  bbInf?: ISeriesApi<"Line">;
  vwap?: ISeriesApi<"Line">;
  rsi?: ISeriesApi<"Line">;
  macdHist?: ISeriesApi<"Histogram">;
  macd?: ISeriesApi<"Line">;
  macdSinal?: ISeriesApi<"Line">;
}

/** Carga completa (histórico novo): setData em todas as séries de indicadores. */
function preencherIndicadores(s: SeriesIndicadores, inc: IndicadoresIncrementais, tempos: UTCTimestamp[]): void {
  const x = inc.series();
  s.ema9?.setData(linha(x.ema9, tempos));
  s.ema21?.setData(linha(x.ema21, tempos));
  s.bbSup?.setData(linha(x.bbSup, tempos));
  s.bbMedia?.setData(linha(x.bbMedia, tempos));
  s.bbInf?.setData(linha(x.bbInf, tempos));
  s.vwap?.setData(linha(x.vwap, tempos));
  s.rsi?.setData(linha(x.rsi, tempos));
  s.macd?.setData(linha(x.macd, tempos));
  s.macdSinal?.setData(linha(x.macdSinal, tempos));
  s.macdHist?.setData(x.macdHist.map((h, i) => (h === null ? { time: tempos[i]! } : { time: tempos[i]!, value: h, color: corHist(h) })));
}

/** Tick: só o ponto da barra tocada (update), sem setData. `historico`: a barra não é a última (oficial atrasado). */
function atualizarIndicadores(
  s: SeriesIndicadores,
  inc: IndicadoresIncrementais,
  i: number,
  time: UTCTimestamp,
  historico = false,
): void {
  const p = inc.ponto(i);
  const up = (serie: ISeriesApi<"Line"> | undefined, v: number | null) =>
    serie?.update(v === null ? { time } : { time, value: v }, historico);
  up(s.ema9, p.ema9);
  up(s.ema21, p.ema21);
  up(s.bbSup, p.bbSup);
  up(s.bbMedia, p.bbMedia);
  up(s.bbInf, p.bbInf);
  up(s.vwap, p.vwap);
  up(s.rsi, p.rsi);
  up(s.macd, p.macd);
  up(s.macdSinal, p.macdSinal);
  s.macdHist?.update(p.macdHist === null ? { time } : { time, value: p.macdHist, color: corHist(p.macdHist) }, historico);
}

const SEM_ROTULO = { lastValueVisible: false, priceLineVisible: false, crosshairMarkerVisible: false } as const;

export function Grafico({
  candles,
  canal,
  tempo,
  indicadores,
  paineis,
  desenhos,
  ferramenta,
  aoCriarDesenho,
  rotulo,
}: {
  /** Histórico fechado (REST). Os ticks ao vivo chegam pelo canal e são aplicados direto no gráfico. */
  candles: Candle[];
  /** `candles:SIMB:tg` da série exibida (também identifica a série para a legenda). */
  canal: CanalCandles | null;
  tempo: TempoGrafico;
  indicadores: IndicadoresGrafico;
  /** RSI e MACD em painéis próprios (modo Avançado). */
  paineis: boolean;
  desenhos: Desenho[];
  ferramenta: Ferramenta;
  aoCriarDesenho: (d: Desenho) => void;
  rotulo: string;
}) {
  const raiz = useRef<HTMLDivElement>(null);
  const caixa = useRef<HTMLDivElement>(null);
  const grafico = useRef<IChartApi | null>(null);
  const velas = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volume = useRef<ISeriesApi<"Histogram"> | null>(null);
  const zonas = useRef<PrimitivaZonas | null>(null);
  const linhas = useRef<IPriceLine[]>([]);
  const linhaPreco = useRef<IPriceLine | null>(null);
  const ind = useRef<SeriesIndicadores>({ lista: [] });
  const agrupador = useRef<AgrupadorQuadros<{ canal: string; tick: CandleAoVivo }> | null>(null);
  const canalCarregado = useRef<string | null>(null);
  const focoRef = useRef<{ chave: string; candle: Candle } | null>(null);
  const legenda = useRef<{ o: HTMLSpanElement | null; h: HTMLSpanElement | null; l: HTMLSpanElement | null; c: HTMLSpanElement | null }>({
    o: null,
    h: null,
    l: null,
    c: null,
  });
  const canalRef = useRef(canal);
  const tempoRef = useRef(tempo);
  const ferramentaRef = useRef(ferramenta);
  const aoCriarRef = useRef(aoCriarDesenho);
  const pendenteRef = useRef<number | null>(null);
  const [pendente, setPendente] = useState<number | null>(null);
  const [serie] = useState(() => new SerieAoVivo());
  const [inc] = useState(() => new IndicadoresIncrementais());
  const diario = TEMPOS_DIARIOS.includes(tempo);

  useEffect(() => {
    canalRef.current = canal;
    tempoRef.current = tempo;
    ferramentaRef.current = ferramenta;
    aoCriarRef.current = aoCriarDesenho;
    if (ferramenta !== "zona") pendenteRef.current = null;
  });

  /** Legenda OHLC: candle do cursor (se for desta série) ou o último. Escrita direto no DOM. */
  function desenharLegenda() {
    const k = legendaVisivel(focoRef.current, canalRef.current ?? "", serie.candles);
    const cor = !k || numero(k.c) >= numero(k.o) ? "text-alta" : "text-baixa";
    const l = legenda.current;
    for (const [campo, el] of [
      ["o", l.o],
      ["h", l.h],
      ["l", l.l],
      ["c", l.c],
    ] as const) {
      if (!el) continue;
      el.textContent = k ? formatarPreco(k[campo]) : "—";
      el.className = cor;
    }
  }

  /** Rótulo do último preço no eixo: cor da barra (alta/baixa) e contagem até o fechamento. */
  function atualizarRotuloPreco() {
    const v = velas.current;
    const ultimo = serie.candles.at(-1);
    if (!v || !ultimo) return;
    const agora = agoraServidor(Date.now());
    const fecha = proximoFechamento(ultimo.t, duracaoTempo(tempoRef.current), agora);
    const title = formatarContagemVela(fecha - agora);
    const color = numero(ultimo.c) >= numero(ultimo.o) ? COR.alta : COR.baixa;
    const price = numero(ultimo.c);
    if (!linhaPreco.current) {
      linhaPreco.current = v.createPriceLine({ price, color, lineWidth: 1, lineStyle: LineStyle.Dotted, axisLabelVisible: true, title });
    } else {
      linhaPreco.current.applyOptions({ price, color, title });
    }
  }

  /** Depois de qualquer mudança na última barra: preço, legenda, atributos para testes e preço ao vivo. */
  function aposMudanca() {
    const ultimo = serie.candles.at(-1);
    atualizarRotuloPreco();
    desenharLegenda();
    const el = raiz.current;
    if (el) {
      el.dataset.barras = String(serie.candles.length);
      el.dataset.ultimoFechamento = ultimo?.c ?? "";
    }
    const simbolo = serie.canal?.split(":")[1];
    if (simbolo && ultimo) publicarPreco(simbolo, ultimo.c);
  }

  /**
   * Um quadro de ticks: aplica na série e atualiza só as barras tocadas, em ordem de tempo. Uma barra anterior
   * à última (1m oficial atrasado) usa a atualização histórica do gráfico, e os indicadores são reescritos
   * dela até o fim (dependem das barras anteriores).
   */
  function descarregar(itens: { canal: string; tick: CandleAoVivo }[]) {
    const v = velas.current;
    const vol = volume.current;
    if (!v || !vol) return;
    const tocados = serie.aplicarLote(itens);
    if (tocados.length === 0) return;
    const ultimo = serie.candles.length - 1;
    const tempos = (i: number) => paraTempo(serie.candles[i]!.t, tempoRef.current);
    let desde = Infinity;
    for (const i of tocados) {
      const k = serie.candles[i]!;
      const time = tempos(i);
      v.update(barra(k, time), i < ultimo);
      vol.update(barraVolume(k, time), i < ultimo);
      desde = Math.min(desde, inc.aplicar(numerico(k)).desde);
    }
    for (let i = desde; i <= ultimo; i++) atualizarIndicadores(ind.current, inc, i, tempos(i), i < ultimo);
    aposMudanca();
  }

  // Criação do gráfico (uma vez).
  useEffect(() => {
    const el = caixa.current;
    if (!el) return;
    const chart = createChart(el, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: COR.fundo },
        textColor: COR.texto,
        fontFamily: "var(--fonte-mono), ui-monospace, monospace",
        fontSize: 11,
        attributionLogo: true,
        panes: { separatorColor: COR.borda, separatorHoverColor: "#283241", enableResize: true },
      },
      grid: { vertLines: { color: COR.grade }, horzLines: { color: COR.grade } },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: "#3a4556", labelBackgroundColor: "#283241" },
        horzLine: { color: "#3a4556", labelBackgroundColor: "#283241" },
      },
      rightPriceScale: { borderColor: COR.borda },
      timeScale: { borderColor: COR.borda, timeVisible: true, secondsVisible: false, rightOffset: 6 },
      localization: { locale: "pt-BR" },
    });
    const v = chart.addSeries(CandlestickSeries, {
      upColor: COR.alta,
      downColor: COR.baixa,
      borderVisible: false,
      wickUpColor: COR.alta,
      wickDownColor: COR.baixa,
      // Linha e rótulo do último preço são desenhados por nós (cor da barra + contagem até o fechamento).
      lastValueVisible: false,
      priceLineVisible: false,
    });
    const vol = chart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
      lastValueVisible: false,
      priceLineVisible: false,
    });
    vol.priceScale().applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
    const z = new PrimitivaZonas();
    v.attachPrimitive(z);


    const clique = (p: MouseEventParams<Time>) => {
      const modo = ferramentaRef.current;
      if (modo === "cursor" || !p.point) return;
      const preco = v.coordinateToPrice(p.point.y);
      if (preco === null) return;
      const valor = Number(preco);
      if (modo === "linha") {
        aoCriarRef.current({ id: novoId(), tipo: "linha", preco: valor });
      } else if (pendenteRef.current === null) {
        pendenteRef.current = valor;
        setPendente(valor);
      } else {
        const inicio = pendenteRef.current;
        pendenteRef.current = null;
        setPendente(null);
        aoCriarRef.current({ id: novoId(), tipo: "zona", de: Math.min(inicio, valor), ate: Math.max(inicio, valor) });
      }
    };
    const porTempo = (time: Time | undefined) => {
      if (time === undefined) return undefined;
      return serie.candles.find((k) => paraTempo(k.t, tempoRef.current) === (time as number));
    };
    const mover = (p: MouseEventParams<Time>) => {
      const candle = porTempo(p.time);
      focoRef.current = candle ? { chave: canalRef.current ?? "", candle } : null;
      desenharLegenda();
    };
    chart.subscribeClick(clique);
    chart.subscribeCrosshairMove(mover);

    grafico.current = chart;
    velas.current = v;
    volume.current = vol;
    zonas.current = z;
    const ag = new AgrupadorQuadros<{ canal: string; tick: CandleAoVivo }>((itens) => descarregar(itens));
    agrupador.current = ag;
    return () => {
      ag.descartar();
      agrupador.current = null;
      chart.unsubscribeClick(clique);
      chart.unsubscribeCrosshairMove(mover);
      chart.remove();
      grafico.current = null;
      velas.current = null;
      volume.current = null;
      zonas.current = null;
      linhas.current = [];
      linhaPreco.current = null;
      ind.current = { lista: [] };
      canalCarregado.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Séries dos indicadores (recriadas quando a seleção muda).
  useEffect(() => {
    const chart = grafico.current;
    if (!chart) return;
    for (const s of ind.current.lista) chart.removeSeries(s);
    const novo: SeriesIndicadores = { lista: [] };
    const add = <T extends SeriesType>(s: ISeriesApi<T>) => {
      novo.lista.push(s as unknown as ISeriesApi<SeriesType>);
      return s;
    };
    if (indicadores.ema) {
      novo.ema9 = add(chart.addSeries(LineSeries, { color: COR.ouro, lineWidth: 1, ...SEM_ROTULO, title: "EMA 9" }));
      novo.ema21 = add(chart.addSeries(LineSeries, { color: COR.azul, lineWidth: 1, ...SEM_ROTULO, title: "EMA 21" }));
    }
    if (indicadores.bollinger) {
      novo.bbSup = add(chart.addSeries(LineSeries, { color: COR.cinza, lineWidth: 1, ...SEM_ROTULO }));
      novo.bbMedia = add(chart.addSeries(LineSeries, { color: COR.cinza, lineWidth: 1, lineStyle: LineStyle.Dashed, ...SEM_ROTULO }));
      novo.bbInf = add(chart.addSeries(LineSeries, { color: COR.cinza, lineWidth: 1, ...SEM_ROTULO }));
    }
    // VWAP ancorado em 00:00 UTC: só faz sentido em tempos intradiários.
    if (indicadores.vwap && !diario) {
      novo.vwap = add(chart.addSeries(LineSeries, { color: COR.roxo, lineWidth: 1, lineStyle: LineStyle.Dotted, ...SEM_ROTULO, title: "VWAP" }));
    }
    let painel = 1;
    if (paineis && indicadores.rsi) {
      const r = add(chart.addSeries(LineSeries, { color: COR.roxo, lineWidth: 1, priceLineVisible: false, title: "RSI 14" }, painel));
      r.createPriceLine({ price: 70, color: "#3a4556", lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: false, title: "" });
      r.createPriceLine({ price: 30, color: "#3a4556", lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: false, title: "" });
      novo.rsi = r;
      painel += 1;
    }
    if (paineis && indicadores.macd) {
      novo.macdHist = add(chart.addSeries(HistogramSeries, { priceLineVisible: false, lastValueVisible: false }, painel));
      novo.macd = add(chart.addSeries(LineSeries, { color: COR.azul, lineWidth: 1, ...SEM_ROTULO, title: "MACD" }, painel));
      novo.macdSinal = add(chart.addSeries(LineSeries, { color: COR.ouro, lineWidth: 1, ...SEM_ROTULO }, painel));
      painel += 1;
    }
    const panes = chart.panes();
    for (let i = 1; i < panes.length; i++) panes[i]?.setHeight(110);
    ind.current = novo;
    preencherIndicadores(novo, inc, serie.candles.map((k) => paraTempo(k.t, tempoRef.current)));
  }, [indicadores.ema, indicadores.bollinger, indicadores.vwap, indicadores.rsi, indicadores.macd, paineis, diario]);


  // Histórico (REST): carga completa. Também roda após reconectar (o Terminal recarrega o REST).
  useEffect(() => {
    const chart = grafico.current;
    const v = velas.current;
    const vol = volume.current;
    if (!chart || !v || !vol || !canal) return;
    serie.carregar(canal, candles);
    const tempos = serie.candles.map((k) => paraTempo(k.t, tempo));
    v.setData(serie.candles.map((k, i) => barra(k, tempos[i]!)));
    vol.setData(serie.candles.map((k, i) => barraVolume(k, tempos[i]!)));
    inc.carregar(serie.candles.map(numerico));
    preencherIndicadores(ind.current, inc, tempos);
    if (canalCarregado.current !== canal && serie.candles.length > 0) {
      const n = serie.candles.length;
      chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, n - 140), to: n + 4 });
    }
    canalCarregado.current = canal;
    focoRef.current = null;
    aposMudanca();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [candles, canal, tempo]);

  // Ticks ao vivo: enfileirados e aplicados uma vez por quadro (sem re-render do React).
  useCanal(canal, (tick, origem) => agrupador.current?.enfileirar({ canal: origem, tick }));
  // Ao trocar de canal (cancelar a assinatura), o que ficou guardado dele é descartado.
  useEffect(() => {
    if (!canal) return;
    return () => serie.descartarEspera(canal);
  }, [canal, serie]);

  // Contagem até o fechamento no rótulo do preço.
  useEffect(() => {
    const id = setInterval(() => atualizarRotuloPreco(), 1000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Desenhos: linhas horizontais (price lines) e zonas (primitiva).
  useEffect(() => {
    const v = velas.current;
    if (!v) return;
    for (const l of linhas.current) v.removePriceLine(l);
    linhas.current = desenhos
      .filter((d): d is Extract<Desenho, { tipo: "linha" }> => d.tipo === "linha")
      .map((d) =>
        v.createPriceLine({ price: d.preco, color: COR.ouro, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: "" }),
      );
    zonas.current?.definir(
      desenhos.filter((d): d is Extract<Desenho, { tipo: "zona" }> => d.tipo === "zona").map((d) => ({ de: d.de, ate: d.ate })),
    );
  }, [desenhos]);


  function zoom(fator: number) {
    const ts = grafico.current?.timeScale();
    const r = ts?.getVisibleLogicalRange();
    if (!ts || !r) return;
    const centro = (r.from + r.to) / 2;
    const meia = Math.max(10, ((r.to - r.from) / 2) * fator);
    ts.setVisibleLogicalRange({ from: centro - meia, to: centro + meia });
  }


  return (
    <div ref={raiz} data-testid="grafico" className="relative flex min-h-[340px] flex-1 flex-col">
      <div className="pointer-events-none absolute top-2 left-3 z-10 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[11px]">
        <span className="num text-apagado" data-testid="legenda-ohlc">
          A <span ref={(el) => void (legenda.current.o = el)}>—</span> M{" "}
          <span ref={(el) => void (legenda.current.h = el)}>—</span> m{" "}
          <span ref={(el) => void (legenda.current.l = el)}>—</span> F{" "}
          <span ref={(el) => void (legenda.current.c = el)} data-testid="ultimo-fechamento">
            —
          </span>
        </span>
        {indicadores.ema && (
          <span className="text-apagado">
            <span className="text-ouro">EMA 9</span> · <span className="text-info">EMA 21</span>
          </span>
        )}
        {pendente !== null && (
          <span className="rounded bg-ouro/15 px-1.5 py-0.5 text-ouro">
            Zona a partir de {formatarPreco(pendente)}: clique no segundo nível
          </span>
        )}
      </div>
      <div className="absolute right-16 bottom-8 z-10 flex gap-1">
        <button type="button" onClick={() => zoom(0.7)} aria-label="Aproximar" className="size-7 rounded border border-borda bg-painel/90 text-sm text-suave hover:text-texto">
          +
        </button>
        <button type="button" onClick={() => zoom(1.4)} aria-label="Afastar" className="size-7 rounded border border-borda bg-painel/90 text-sm text-suave hover:text-texto">
          −
        </button>
        <button
          type="button"
          onClick={() => grafico.current?.timeScale().fitContent()}
          aria-label="Ajustar ao conteúdo"
          className="h-7 rounded border border-borda bg-painel/90 px-2 text-[11px] text-suave hover:text-texto"
        >
          Ajustar
        </button>
      </div>
      <div
        ref={caixa}
        role="img"
        aria-label={rotulo}
        className={`min-h-0 flex-1 ${ferramenta === "cursor" ? "" : "cursor-crosshair"}`}
      />
    </div>
  );
}
