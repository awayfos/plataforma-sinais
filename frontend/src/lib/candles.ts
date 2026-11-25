import type { Candle } from "./api/tipos";

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
