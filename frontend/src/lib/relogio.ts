// Relógio do servidor estimado pelo cabeçalho HTTP Date (resolução de 1 s).
// A janela de entrada (`janela_ate`) é do relógio do servidor; o do navegador pode estar adiantado ou atrasado.

/** Margem de segurança descontada da janela de entrada (latência e erro da estimativa). */
export const MARGEM_JANELA_MS = 1_000;

/** Amostras recentes usadas na estimativa (a mediana ignora uma resposta lenta ou um salto isolado). */
export const AMOSTRAS_RELOGIO = 7;

let amostras: number[] = [];
let deslocamentoMs = 0;

function mediana(valores: number[]): number {
  const ordenados = [...valores].sort((a, b) => a - b);
  const meio = Math.floor(ordenados.length / 2);
  return ordenados.length % 2 ? ordenados[meio]! : (ordenados[meio - 1]! + ordenados[meio]!) / 2;
}

/**
 * Registra a hora do servidor vista numa resposta. O Date trunca para o segundo, então o instante real fica
 * em [D, D + 1 s): usa o meio do intervalo. O deslocamento é a mediana das últimas `AMOSTRAS_RELOGIO`
 * amostras: a contagem não pula de um lado para o outro a cada resposta.
 */
export function registrarHoraServidor(cabecalhoDate: string | null, recebidoEm: number): void {
  if (!cabecalhoDate) return;
  const servidor = Date.parse(cabecalhoDate);
  if (!Number.isFinite(servidor)) return;
  amostras = [...amostras, servidor + 500 - recebidoEm].slice(-AMOSTRAS_RELOGIO);
  deslocamentoMs = mediana(amostras);
}

/** Converte um instante do relógio local para o relógio estimado do servidor. */
export function agoraServidor(agoraLocal: number): number {
  return agoraLocal + deslocamentoMs;
}

export function deslocamentoAtual(): number {
  return deslocamentoMs;
}

/** Só para testes. */
export function redefinirRelogio(): void {
  amostras = [];
  deslocamentoMs = 0;
}
