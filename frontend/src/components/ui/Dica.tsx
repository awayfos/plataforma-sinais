"use client";

import { useEffect, useId, useRef, useState } from "react";
import { glossario, type TermoGlossario } from "@/lib/glossario";

/** Ícone "aprenda" ao lado de cada termo técnico (design §5, item 7). */
export function Dica({ termo, lado = "baixo" }: { termo: TermoGlossario; lado?: "baixo" | "cima" }) {
  const [aberta, setAberta] = useState(false);
  const id = useId();
  const raiz = useRef<HTMLSpanElement>(null);
  const item = glossario[termo];

  useEffect(() => {
    if (!aberta) return;
    const tecla = (e: KeyboardEvent) => {
      if (e.key === "Escape") setAberta(false);
    };
    const fora = (e: PointerEvent) => {
      if (raiz.current && !raiz.current.contains(e.target as Node)) setAberta(false);
    };
    document.addEventListener("keydown", tecla);
    document.addEventListener("pointerdown", fora);
    return () => {
      document.removeEventListener("keydown", tecla);
      document.removeEventListener("pointerdown", fora);
    };
  }, [aberta]);

  return (
    <span ref={raiz} className="relative inline-flex align-middle">
      <button
        type="button"
        aria-label={`Aprenda: ${item.titulo}`}
        aria-expanded={aberta}
        aria-describedby={aberta ? id : undefined}
        onClick={() => setAberta((v) => !v)}
        className="ml-1 inline-flex size-3.5 items-center justify-center rounded-full border border-borda-forte text-[9px] leading-none font-semibold text-apagado transition-colors hover:border-ouro hover:text-ouro focus-visible:border-ouro focus-visible:text-ouro"
      >
        ?
      </button>
      {aberta && (
        <span
          role="tooltip"
          id={id}
          className={`absolute left-1/2 z-50 w-72 -translate-x-1/2 rounded-md border border-borda-forte bg-painel-2 p-3 text-left text-xs leading-relaxed font-normal tracking-normal text-suave normal-case shadow-2xl shadow-black/60 ${
            lado === "baixo" ? "top-full mt-2" : "bottom-full mb-2"
          }`}
        >
          <span className="mb-1 block text-[11px] font-semibold tracking-wide text-ouro uppercase">Aprenda · {item.titulo}</span>
          {item.texto}
        </span>
      )}
    </span>
  );
}
