import type { ReactNode } from "react";

export function Carregando({ rotulo = "Carregando…", linhas = 3 }: { rotulo?: string; linhas?: number }) {
  return (
    <div role="status" aria-live="polite" className="space-y-2 p-1">
      <span className="sr-only">{rotulo}</span>
      {Array.from({ length: linhas }, (_, i) => (
        <div key={i} className="h-3 animate-pulse rounded bg-painel-2" style={{ width: `${90 - i * 15}%` }} />
      ))}
    </div>
  );
}

export function Vazio({ titulo, children }: { titulo: string; children?: ReactNode }) {
  return (
    <div className="rounded-md border border-dashed border-borda px-4 py-6 text-center">
      <p className="text-sm font-medium text-texto">{titulo}</p>
      {children && <div className="mx-auto mt-1 max-w-md text-xs leading-relaxed text-apagado">{children}</div>}
    </div>
  );
}

export function ErroEstado({ mensagem, aoTentarDeNovo }: { mensagem: string; aoTentarDeNovo?: () => void }) {
  return (
    <div role="alert" className="flex items-start justify-between gap-3 rounded-md border border-baixa/30 bg-baixa/5 px-3 py-2.5 text-xs text-baixa">
      <span>{mensagem}</span>
      {aoTentarDeNovo && (
        <button type="button" onClick={aoTentarDeNovo} className="shrink-0 font-medium underline underline-offset-2 hover:text-texto">
          Tentar de novo
        </button>
      )}
    </div>
  );
}
