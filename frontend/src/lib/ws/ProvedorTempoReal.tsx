"use client";

import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { irParaLogin } from "@/components/sessao/ProvedorSessao";
import { ClienteTempoReal, urlTempoReal, type Canal, type DadosDoCanal, type StatusConexao } from "./cliente";

interface ValorTempoReal {
  cliente: ClienteTempoReal | null;
  status: StatusConexao;
}

const Contexto = createContext<ValorTempoReal>({ cliente: null, status: "ocioso" });

export function ProvedorTempoReal({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<StatusConexao>("ocioso");
  const [cliente] = useState(() =>
    typeof window === "undefined"
      ? null
      : new ClienteTempoReal({
          url: urlTempoReal(),
          aoMudarStatus: setStatus,
          aoSessaoRevogada: irParaLogin,
          aoAssinaturaVencida: () => window.location.assign("/assinatura"),
        }),
  );

  useEffect(() => {
    cliente?.retomar();
    return () => cliente?.fechar();
  }, [cliente]);

  return <Contexto.Provider value={{ cliente, status }}>{children}</Contexto.Provider>;
}

export function useStatusTempoReal(): StatusConexao {
  return useContext(Contexto).status;
}

/** Assina um canal enquanto o componente estiver montado (null = nenhum). */
export function usarCanal<C extends Canal>(canal: C | null, ouvinte: (dados: DadosDoCanal<C>) => void): void {
  const { cliente } = useContext(Contexto);
  const ref = useRef(ouvinte);
  useEffect(() => {
    ref.current = ouvinte;
  });
  useEffect(() => {
    if (!cliente || !canal) return;
    return cliente.assinar(canal, (dados) => ref.current(dados));
  }, [cliente, canal]);
}
