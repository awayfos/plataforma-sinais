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
import type { Candle, Desenho, IndicadoresGrafico } from "@/lib/api/tipos";
import { numero } from "@/lib/candles";
import { formatarPreco } from "@/lib/formato";
import { bollinger, ema, macd, rsi, vwap, type Serie } from "@/lib/indicadores";
import { PrimitivaZonas } from "./primitivaZona";

export type Ferramenta = "cursor" | "linha" | "zona";

/** O Brasil não tem horário de verão desde 2019: o eixo mostra UTC−3 (Brasília). */
const DESLOCAMENTO_BRASILIA_S = -3 * 3600;
const paraTempo = (ms: number) => (Math.floor(ms / 1000) + DESLOCAMENTO_BRASILIA_S) as UTCTimestamp;

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

function preencherIndicadores(s: SeriesIndicadores, candles: Candle[]): void {
  const tempos = candles.map((k) => paraTempo(k.t));
  const fechamentos = candles.map((k) => numero(k.c));
  if (s.ema9 && s.ema21) {
    s.ema9.setData(linha(ema(fechamentos, 9), tempos));
    s.ema21.setData(linha(ema(fechamentos, 21), tempos));
  }
  if (s.bbSup && s.bbMedia && s.bbInf) {
    const b = bollinger(fechamentos, 20, 2);
    s.bbSup.setData(linha(b.superior, tempos));
    s.bbMedia.setData(linha(b.media, tempos));
    s.bbInf.setData(linha(b.inferior, tempos));
  }
  if (s.vwap) {
    s.vwap.setData(linha(vwap(candles.map((k) => ({ t: k.t, h: numero(k.h), l: numero(k.l), c: numero(k.c), v: numero(k.v) }))), tempos));
  }
  if (s.rsi) s.rsi.setData(linha(rsi(fechamentos, 14), tempos));
  if (s.macdHist && s.macd && s.macdSinal) {
    const m = macd(fechamentos);
    s.macd.setData(linha(m.macd, tempos));
    s.macdSinal.setData(linha(m.sinal, tempos));
    s.macdHist.setData(
      m.histograma.map((h, i) =>
        h === null
          ? { time: tempos[i]! }
          : { time: tempos[i]!, value: h, color: h >= 0 ? "rgba(38, 181, 140, 0.6)" : "rgba(240, 97, 109, 0.6)" },
      ),
    );
  }
}

const SEM_ROTULO = { lastValueVisible: false, priceLineVisible: false, crosshairMarkerVisible: false } as const;

export function Grafico({
  candles,
  indicadores,
  paineis,
  desenhos,
  ferramenta,
  aoCriarDesenho,
  rotulo,
}: {
  candles: Candle[];
  indicadores: IndicadoresGrafico;
  /** RSI e MACD em painéis próprios (modo Avançado). */
  paineis: boolean;
  desenhos: Desenho[];
  ferramenta: Ferramenta;
  aoCriarDesenho: (d: Desenho) => void;
  rotulo: string;
}) {
  const caixa = useRef<HTMLDivElement>(null);
  const grafico = useRef<IChartApi | null>(null);
  const velas = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volume = useRef<ISeriesApi<"Histogram"> | null>(null);
  const zonas = useRef<PrimitivaZonas | null>(null);
  const linhas = useRef<IPriceLine[]>([]);
  const ind = useRef<SeriesIndicadores>({ lista: [] });
  const carregado = useRef<{ primeiro: number; n: number } | null>(null);
  const porTempo = useRef(new Map<number, Candle>());
  const ferramentaRef = useRef(ferramenta);
  const aoCriarRef = useRef(aoCriarDesenho);
  const pendenteRef = useRef<number | null>(null);
  const [pendente, setPendente] = useState<number | null>(null);
  const [foco, setFoco] = useState<Candle | null>(null);
  const ultimos = useRef<Candle[]>([]);

  useEffect(() => {
    ferramentaRef.current = ferramenta;
    aoCriarRef.current = aoCriarDesenho;
    if (ferramenta !== "zona") pendenteRef.current = null;
  });

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
      priceLineColor: "#3a4556",
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
    const mover = (p: MouseEventParams<Time>) => {
      setFoco(p.time === undefined ? null : (porTempo.current.get(p.time as number) ?? null));
    };
    chart.subscribeClick(clique);
    chart.subscribeCrosshairMove(mover);

    grafico.current = chart;
    velas.current = v;
    volume.current = vol;
    zonas.current = z;
    return () => {
      chart.unsubscribeClick(clique);
      chart.unsubscribeCrosshairMove(mover);
      chart.remove();
      grafico.current = null;
      velas.current = null;
      volume.current = null;
      zonas.current = null;
      linhas.current = [];
      ind.current = { lista: [] };
      carregado.current = null;
    };
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
    if (indicadores.vwap) {
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
    preencherIndicadores(novo, ultimos.current);
  }, [indicadores.ema, indicadores.bollinger, indicadores.vwap, indicadores.rsi, indicadores.macd, paineis]);

  // Dados: candles, volume e indicadores.
  useEffect(() => {
    const chart = grafico.current;
    const v = velas.current;
    const vol = volume.current;
    if (!chart || !v || !vol) return;
    const tempos = candles.map((k) => paraTempo(k.t));
    const barras = candles.map((k, i) => ({ time: tempos[i]!, open: numero(k.o), high: numero(k.h), low: numero(k.l), close: numero(k.c) }));
    const volumes = candles.map((k, i) => ({
      time: tempos[i]!,
      value: numero(k.v),
      color: numero(k.c) >= numero(k.o) ? "rgba(38, 181, 140, 0.32)" : "rgba(240, 97, 109, 0.32)",
    }));
    porTempo.current = new Map(candles.map((k, i) => [tempos[i]!, k]));

    const anterior = carregado.current;
    const primeiro = candles[0]?.t ?? -1;
    const incremental =
      anterior !== null && anterior.primeiro === primeiro && candles.length > 0 && (candles.length === anterior.n || candles.length === anterior.n + 1);
    if (incremental) {
      v.update(barras.at(-1)!);
      vol.update(volumes.at(-1)!);
    } else {
      v.setData(barras);
      vol.setData(volumes);
      if (anterior?.primeiro !== primeiro && candles.length > 0) {
        chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, candles.length - 140), to: candles.length + 4 });
      }
    }
    carregado.current = { primeiro, n: candles.length };

    ultimos.current = candles;
    preencherIndicadores(ind.current, candles);
  }, [candles]);

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

  const vela = foco ?? candles.at(-1) ?? null;
  const subiu = vela ? numero(vela.c) >= numero(vela.o) : true;

  return (
    <div className="relative flex min-h-[340px] flex-1 flex-col">
      <div className="pointer-events-none absolute top-2 left-3 z-10 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[11px]">
        {vela && (
          <span className="num text-apagado" data-testid="legenda-ohlc">
            A <span className={subiu ? "text-alta" : "text-baixa"}>{formatarPreco(vela.o)}</span> M{" "}
            <span className={subiu ? "text-alta" : "text-baixa"}>{formatarPreco(vela.h)}</span> m{" "}
            <span className={subiu ? "text-alta" : "text-baixa"}>{formatarPreco(vela.l)}</span> F{" "}
            <span className={subiu ? "text-alta" : "text-baixa"} data-testid="ultimo-fechamento">
              {formatarPreco(vela.c)}
            </span>
          </span>
        )}
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
