"use client";

import type { Ativo } from "@/lib/api/tipos";
import { PrecoAoVivo } from "./PrecoAoVivo";

export function ListaAtivos({
  ativos,
  selecionado,
  aoSelecionar,
}: {
  ativos: Ativo[];
  selecionado: string | null;
  aoSelecionar: (simbolo: string) => void;
}) {
  return (
    <ul className="flex gap-1 lg:flex-col" aria-label="Ativos">
      {ativos.map((a) => {
        const ativo = a.simbolo === selecionado;
        return (
          <li key={a.simbolo} className="min-w-36 lg:min-w-0">
            <button
              type="button"
              disabled={!a.aberto}
              aria-current={ativo ? "true" : undefined}
              onClick={() => aoSelecionar(a.simbolo)}
              className={`group flex w-full items-center justify-between gap-3 rounded-md border px-3 py-2 text-left transition-colors ${
                ativo
                  ? "border-ouro/40 bg-ouro/[0.06]"
                  : "border-transparent hover:border-borda hover:bg-painel-2 disabled:hover:border-transparent disabled:hover:bg-transparent"
              } disabled:cursor-not-allowed disabled:opacity-50`}
            >
              <span className="min-w-0">
                <span className="num block text-[13px] font-semibold text-texto">{a.simbolo}</span>
                <span className="block truncate text-[11px] text-apagado">{a.nome}</span>
                {a.aberto && <PrecoAoVivo simbolo={a.simbolo} className="mt-0.5 block text-[12px]" />}
              </span>
              <span
                className={`inline-flex items-center gap-1 text-[10px] font-medium tracking-wide uppercase ${
                  a.aberto ? "text-alta" : "text-apagado"
                }`}
              >
                <span className={`size-1.5 rounded-full ${a.aberto ? "bg-alta" : "bg-apagado"}`} aria-hidden="true" />
                {a.aberto ? "Aberto" : "Fechado"}
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
