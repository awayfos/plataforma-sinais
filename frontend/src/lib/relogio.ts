// Relógio do servidor estimado pelo cabeçalho HTTP Date (resolução de 1 s).
// A janela de entrada (`janela_ate`) é do relógio do servidor; o do navegador pode estar adiantado ou atrasado.

/** Margem de segurança descontada da janela de entrada (latência e erro da estimativa). */
export const MARGEM_JANELA_MS = 1_000;

let deslocamentoMs = 0;

/**
 * Registra a hora do servidor vista numa resposta. O Date trunca para o segundo, então o instante real fica
 * em [D, D + 1 s): usa o meio do intervalo.
 */
export function registrarHoraServidor(cabecalhoDate: string | null, recebidoEm: number): void {
  if (!cabecalhoDate) return;
  const servidor = Date.parse(cabecalhoDate);
  if (!Number.isFinite(servidor)) return;
  deslocamentoMs = servidor + 500 - recebidoEm;
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
  deslocamentoMs = 0;
}
