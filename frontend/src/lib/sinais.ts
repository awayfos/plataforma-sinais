import { EXPIRACOES, type Expiracao, type Sinal, type SinalHistorico } from "./api/tipos";

export const ROTULO_EXPIRACAO: Record<Expiracao, string> = {
  "1m": "1 min",
  "5m": "5 min",
  "15m": "15 min",
  "30m": "30 min",
  "60m": "1 h",
};

export const EXPIRACOES_CURTAS: readonly Expiracao[] = ["1m", "5m"];

export function ordenarSinais(lista: Sinal[]): { expiracao: Expiracao; sinal: Sinal | null }[] {
  return EXPIRACOES.map((expiracao) => ({
    expiracao,
    sinal: lista.find((s) => s.expiracao === expiracao) ?? null,
  }));
}

export function estadoJanela(janelaAte: number | null, agora: number): { dentro: boolean; restanteMs: number } {
  if (janelaAte === null || agora > janelaAte) return { dentro: false, restanteMs: 0 };
  return { dentro: true, restanteMs: janelaAte - agora };
}

export interface Estatisticas {
  /** Liquidados com dado (WIN + LOSS + TIE). */
  n: number;
  win: number;
  loss: number;
  tie: number;
  semDado: number;
  pendentes: number;
  apertados: number;
  /** WIN / (WIN + LOSS); empate devolve o valor e fica à parte. */
  taxa: number | null;
}

export function estatisticas(historico: SinalHistorico[]): Estatisticas {
  let win = 0;
  let loss = 0;
  let tie = 0;
  let semDado = 0;
  let pendentes = 0;
  let apertados = 0;
  for (const h of historico) {
    if (h.resultado === "WIN") win++;
    else if (h.resultado === "LOSS") loss++;
    else if (h.resultado === "TIE") tie++;
    else if (h.resultado === "SEM_DADO") semDado++;
    else pendentes++;
    if (h.apertado && h.resultado !== null && h.resultado !== "SEM_DADO") apertados++;
  }
  const decididos = win + loss;
  return { n: win + loss + tie, win, loss, tie, semDado, pendentes, apertados, taxa: decididos > 0 ? win / decididos : null };
}
