/** Aviso de risco permanente e discreto (design §15). */
export function AvisoRisco() {
  return (
    <aside
      aria-label="Aviso de risco"
      className="border-t border-borda bg-fundo/95 px-4 py-1.5 text-[11px] leading-snug text-apagado backdrop-blur"
    >
      <span className="font-semibold text-alerta">Aviso de risco:</span> opções binárias têm alto risco e você pode perder todo o
      valor investido. Esta plataforma não é recomendação de investimento e não garante resultado. Probabilidades são
      estimativas de desempenho passado, em dados fora da amostra.
    </aside>
  );
}
