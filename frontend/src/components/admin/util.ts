import { FUSO } from "@/lib/formato";

/** "AAAA-MM-DD" (data de Brasília) → ms UTC no início ou no fim do dia em Brasília. */
export function dataParaMs(data: string, fimDoDia = false): number {
  return Date.parse(`${data}T${fimDoDia ? "23:59:59.999" : "00:00:00.000"}-03:00`);
}

/** ms UTC → "AAAA-MM-DD" em Brasília (para <input type="date">). */
export function msParaData(ms: number): string {
  const partes = new Intl.DateTimeFormat("en-CA", { timeZone: FUSO, year: "numeric", month: "2-digit", day: "2-digit" }).format(ms);
  return partes;
}

export const EMAIL_VALIDO = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function json(v: unknown): string {
  try {
    return JSON.stringify(v, null, 2);
  } catch {
    return String(v);
  }
}
