"use client";

import { useSyncExternalStore } from "react";
import { formatarPreco } from "@/lib/formato";
import { assinarPrecos, lerPreco, publicarPreco, precoDoCanal } from "@/lib/precos";
import { useCanal } from "@/lib/ws/ProvedorTempoReal";

const nenhum = () => undefined;

/** Último preço com "flash" verde/vermelho a cada mudança (só este nó re-renderiza). */
export function PrecoAoVivo({ simbolo, className = "" }: { simbolo: string; className?: string }) {
  const p = useSyncExternalStore(assinarPrecos, () => lerPreco(simbolo), nenhum);
  const cor = !p || p.direcao === 0 ? "text-texto" : p.direcao > 0 ? "text-alta" : "text-baixa";
  const flash = !p || p.direcao === 0 ? "" : p.direcao > 0 ? "piscar-alta" : "piscar-baixa";
  return (
    <span
      key={p?.seq ?? 0}
      data-testid={`preco-${simbolo}`}
      className={`num rounded-sm px-0.5 tabular-nums ${cor} ${flash} ${className}`}
    >
      {p ? formatarPreco(p.preco) : "—"}
    </span>
  );
}

/** Assina `preco:SIMB` (se o backend publicar) e alimenta o preço ao vivo do ativo. */
export function CanalPreco({ simbolo }: { simbolo: string }) {
  useCanal(`preco:${simbolo}` as const, (dados) => {
    const preco = precoDoCanal(dados);
    if (preco !== null) publicarPreco(simbolo, preco);
  });
  return null;
}
