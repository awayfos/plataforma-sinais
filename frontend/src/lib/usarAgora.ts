"use client";

import { useEffect, useState } from "react";

/** Relógio da tela, atualizado a cada `intervaloMs`. */
export function usarAgora(intervaloMs = 250, ativo = true): number {
  const [agora, setAgora] = useState(() => Date.now());
  useEffect(() => {
    if (!ativo) return;
    const id = setInterval(() => setAgora(Date.now()), intervaloMs);
    return () => clearInterval(id);
  }, [intervaloMs, ativo]);
  return agora;
}
