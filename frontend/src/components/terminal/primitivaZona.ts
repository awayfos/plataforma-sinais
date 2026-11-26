import type {
  IPrimitivePaneRenderer,
  IPrimitivePaneView,
  ISeriesApi,
  ISeriesPrimitive,
  SeriesAttachedParameter,
  SeriesType,
  Time,
} from "lightweight-charts";

type AlvoDesenho = Parameters<IPrimitivePaneRenderer["draw"]>[0];

export interface Zona {
  de: number;
  ate: number;
}

/** Primitiva de série que pinta faixas horizontais de preço (ferramenta "zona de preço"). */
export class PrimitivaZonas implements ISeriesPrimitive<Time> {
  private zonas: Zona[] = [];
  private serie: ISeriesApi<SeriesType> | null = null;
  private pedirAtualizacao: (() => void) | null = null;
  private readonly visoes: readonly IPrimitivePaneView[];

  constructor(private readonly cor = "214, 173, 92") {
    const renderer: IPrimitivePaneRenderer = {
      draw: () => {},
      drawBackground: (alvo: AlvoDesenho) => this.desenhar(alvo),
    };
    this.visoes = [{ zOrder: () => "bottom", renderer: () => renderer }];
  }

  attached(p: SeriesAttachedParameter<Time>): void {
    this.serie = p.series;
    this.pedirAtualizacao = p.requestUpdate;
  }

  detached(): void {
    this.serie = null;
    this.pedirAtualizacao = null;
  }

  definir(zonas: Zona[]): void {
    this.zonas = zonas;
    this.pedirAtualizacao?.();
  }

  updateAllViews(): void {}

  paneViews(): readonly IPrimitivePaneView[] {
    return this.visoes;
  }

  private desenhar(alvo: AlvoDesenho): void {
    const serie = this.serie;
    if (!serie || this.zonas.length === 0) return;
    alvo.useBitmapCoordinateSpace(({ context, bitmapSize, verticalPixelRatio }) => {
      for (const z of this.zonas) {
        const y1 = serie.priceToCoordinate(z.de);
        const y2 = serie.priceToCoordinate(z.ate);
        if (y1 === null || y2 === null) continue;
        const topo = Math.round(Math.min(y1, y2) * verticalPixelRatio);
        const altura = Math.max(1, Math.round(Math.abs(y2 - y1) * verticalPixelRatio));
        context.fillStyle = `rgba(${this.cor}, 0.09)`;
        context.fillRect(0, topo, bitmapSize.width, altura);
        context.fillStyle = `rgba(${this.cor}, 0.55)`;
        const linha = Math.max(1, Math.round(verticalPixelRatio));
        context.fillRect(0, topo, bitmapSize.width, linha);
        context.fillRect(0, topo + altura - linha, bitmapSize.width, linha);
      }
    });
  }
}
