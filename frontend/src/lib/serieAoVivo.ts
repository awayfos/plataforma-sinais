import type { Candle, CandleAoVivo } from "./api/tipos";

export type ResultadoTick =
  | { tipo: "ignorado" }
  | { tipo: "substituido" | "anexado"; indice: number; candle: CandleAoVivo };

/**
 * Série de candles de um canal (`candles:SIMB:tg`): histórico fechado do REST + barra em formação do WebSocket.
 * - mesmo t → substitui a última barra; t maior → nova barra; t menor → ignora;
 * - barra fechada (`fechado: true`, ou vinda do REST) não volta a ser alterada por tick em formação;
 * - tick de outro canal (troca de ativo ou tempo gráfico) é descartado.
 */
export class SerieAoVivo {
  canal: string | null = null;
  candles: CandleAoVivo[] = [];
  /** Ticks que chegaram antes do histórico do canal (ex.: snapshot antes do REST). */
  private espera = new Map<string, CandleAoVivo[]>();

  /** Carrega o histórico. No mesmo canal (ressincronização), mantém as barras ao vivo mais novas que ele. */
  carregar(canal: string, base: Candle[]): void {
    const fechados: CandleAoVivo[] = base.map((c) => ({ ...c, fechado: true }));
    const ultimoBase = fechados.at(-1)?.t ?? -Infinity;
    const vivos = canal === this.canal ? this.candles.filter((c) => c.t > ultimoBase) : [];
    this.canal = canal;
    this.candles = [...fechados, ...vivos];
    const pendentes = this.espera.get(canal) ?? [];
    this.espera.delete(canal);
    for (const tick of pendentes) this.aplicar(canal, tick);
  }

  aplicar(canal: string, tick: CandleAoVivo): ResultadoTick {
    if (canal !== this.canal) {
      // Guarda só para um canal ainda não carregado (a troca de série manda o REST logo em seguida).
      const fila = this.espera.get(canal) ?? [];
      fila.push(tick);
      this.espera.set(canal, fila.slice(-50));
      return { tipo: "ignorado" };
    }
    const ultimo = this.candles.at(-1);
    if (!ultimo || tick.t > ultimo.t) {
      this.candles.push(tick);
      return { tipo: "anexado", indice: this.candles.length - 1, candle: tick };
    }
    if (tick.t < ultimo.t) return { tipo: "ignorado" };
    if (ultimo.fechado && !tick.fechado) return { tipo: "ignorado" };
    const indice = this.candles.length - 1;
    this.candles[indice] = tick;
    return { tipo: "substituido", indice, candle: tick };
  }

  /** Aplica um lote (um quadro) e devolve os índices tocados, cada um uma vez, em ordem. */
  aplicarLote(itens: { canal: string; tick: CandleAoVivo }[]): number[] {
    const tocados = new Set<number>();
    for (const { canal, tick } of itens) {
      const r = this.aplicar(canal, tick);
      if (r.tipo !== "ignorado") tocados.add(r.indice);
    }
    return [...tocados].sort((a, b) => a - b);
  }
}
