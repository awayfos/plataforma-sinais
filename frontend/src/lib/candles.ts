import type { Candle, TempoGrafico } from "./api/tipos";

/** Junta um candle ao vivo à série: substitui o de mesmo t, anexa um novo, ignora um atrasado. */
export function mesclarCandle<T extends Candle>(lista: T[], novo: T): T[] {
  const ultimo = lista.at(-1);
  if (!ultimo) return [novo];
  if (novo.t === ultimo.t) return [...lista.slice(0, -1), novo];
  if (novo.t > ultimo.t) return [...lista, novo];
  return lista;
}

export function numero(v: string | number): number {
  return typeof v === "number" ? v : Number(v);
}

/** O Brasil não tem horário de verão desde 2019: o eixo intradiário mostra UTC−3 (Brasília). */
const DESLOCAMENTO_BRASILIA_S = -3 * 3600;

/** Tempos gráficos cujas barras representam um dia ou mais (abrem 00:00 UTC). */
export const TEMPOS_DIARIOS: readonly TempoGrafico[] = ["1d", "1w"];

/**
 * Instante (s) usado no eixo do gráfico. Intradiário: deslocado para Brasília. Diário e semanal: sem
 * deslocamento, senão a barra de 00:00 UTC apareceria às 21:00 do dia anterior.
 */
export function tempoDoGrafico(ms: number, tempo: TempoGrafico): number {
  const s = Math.floor(ms / 1000);
  return TEMPOS_DIARIOS.includes(tempo) ? s : s + DESLOCAMENTO_BRASILIA_S;
}

/** Candle da legenda: o do cursor se for da série exibida; senão, o último. */
export function legendaVisivel<T extends Candle>(foco: { chave: string; candle: T } | null, chave: string, candles: T[]): T | null {
  if (foco && foco.chave === chave) return foco.candle;
  return candles.at(-1) ?? null;
}
