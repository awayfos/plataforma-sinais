import type { Candle, CandleAoVivo } from "./api/tipos";

export type ResultadoTick =
  | { tipo: "ignorado" }
  | { tipo: "substituido" | "anexado"; indice: number; candle: CandleAoVivo };

/**
 * Série de candles de um canal (`candles:SIMB:tg`): histórico fechado do REST + barra em formação do WebSocket.
 * - mesmo t → substitui a última barra; t maior → nova barra; t menor → ignora;
 * - exceção: `fechado: true` (1m oficial) de uma barra anterior substitui a barra de mesmo t entre as
 *   últimas `BARRAS_RECONCILIAVEIS` — o oficial chega 1–2 s depois dos primeiros ticks da barra seguinte;
 * - barra fechada (`fechado: true`, ou vinda do REST) não volta a ser alterada por tick em formação;
 * - tick de outro canal (troca de ativo ou tempo gráfico) é descartado.
 */
export class SerieAoVivo {
  /** Quantas barras do fim a reconciliação do oficial procura. */
  static readonly BARRAS_RECONCILIAVEIS = 5;
  /** Canais ainda não carregados guardados ao mesmo tempo (os mais antigos saem). */
  static readonly MAX_CANAIS_ESPERA = 3;
  static readonly MAX_TICKS_ESPERA = 50;

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
    // Só o canal exibido interessa: o que sobrou de outros canais (assinaturas antigas) é descartado.
    this.espera.clear();
    for (const tick of pendentes) this.aplicar(canal, tick);
  }

  /** Esquece os ticks guardados de um canal (chamado ao cancelar a assinatura dele). */
  descartarEspera(canal: string): void {
    this.espera.delete(canal);
  }

  canaisEmEspera(): string[] {
    return [...this.espera.keys()];
  }

  aplicar(canal: string, tick: CandleAoVivo): ResultadoTick {
    if (canal !== this.canal) {
      // Guarda só para um canal ainda não carregado (a troca de série manda o REST logo em seguida).
      const fila = this.espera.get(canal) ?? [];
      fila.push(tick);
      this.espera.delete(canal); // reinsere no fim: a ordem do Map é a do uso mais recente
      this.espera.set(canal, fila.slice(-SerieAoVivo.MAX_TICKS_ESPERA));
      while (this.espera.size > SerieAoVivo.MAX_CANAIS_ESPERA) {
        const maisAntigo = this.espera.keys().next().value as string;
        this.espera.delete(maisAntigo);
      }
      return { tipo: "ignorado" };
    }
    const ultimo = this.candles.at(-1);
    if (!ultimo || tick.t > ultimo.t) {
      this.candles.push(tick);
      return { tipo: "anexado", indice: this.candles.length - 1, candle: tick };
    }
    if (tick.t < ultimo.t) return tick.fechado ? this.reconciliar(tick) : { tipo: "ignorado" };
    if (ultimo.fechado && !tick.fechado) return { tipo: "ignorado" };
    const indice = this.candles.length - 1;
    this.candles[indice] = tick;
    return { tipo: "substituido", indice, candle: tick };
  }

  /** Oficial (`fechado: true`) de uma barra anterior à última: substitui a de mesmo t, se estiver entre as últimas. */
  private reconciliar(tick: CandleAoVivo): ResultadoTick {
    const limite = Math.max(0, this.candles.length - 1 - SerieAoVivo.BARRAS_RECONCILIAVEIS);
    for (let i = this.candles.length - 2; i >= limite; i--) {
      const t = this.candles[i]!.t;
      if (t === tick.t) {
        this.candles[i] = tick;
        return { tipo: "substituido", indice: i, candle: tick };
      }
      if (t < tick.t) break;
    }
    return { tipo: "ignorado" };
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
