import type { Direcao } from "@/lib/api/tipos";

const ESTILO: Record<Direcao, { classe: string; icone: string }> = {
  COMPRA: { classe: "border-alta/40 bg-alta/10 text-alta", icone: "▲" },
  VENDA: { classe: "border-baixa/40 bg-baixa/10 text-baixa", icone: "▼" },
  AGUARDAR: { classe: "border-borda-forte bg-painel-2 text-neutro", icone: "■" },
};

export function SeloDirecao({ direcao, grande = false }: { direcao: Direcao; grande?: boolean }) {
  const e = ESTILO[direcao];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded border font-semibold tracking-wide ${e.classe} ${
        grande ? "px-2.5 py-1 text-sm" : "px-1.5 py-0.5 text-[11px]"
      }`}
    >
      <span aria-hidden="true" className="text-[0.7em]">
        {e.icone}
      </span>
      {direcao}
    </span>
  );
}
