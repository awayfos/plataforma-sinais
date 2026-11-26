"use client";

import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { irParaLogin } from "@/components/sessao/ProvedorSessao";
import { api } from "@/lib/api/endpoints";
import {
  ClienteTempoReal,
  urlTempoReal,
  type Canal,
  type DadosDoCanal,
  type OpcoesTempoReal,
  type StatusConexao,
} from "./cliente";

interface ValorTempoReal {
  cliente: ClienteTempoReal | null;
  status: StatusConexao;
  /** Quantas vezes a conexão foi reaberta depois de cair (muda → recarregar dados de REST). */
  reconexoes: number;
}

const Contexto = createContext<ValorTempoReal>({ cliente: null, status: "ocioso", reconexoes: 0 });

export function ProvedorTempoReal({
  children,
  criarSocket,
  agendar,
}: {
  children: ReactNode;
  /** Só para testes: socket e agendador simulados. */
  criarSocket?: OpcoesTempoReal["criarSocket"];
  agendar?: OpcoesTempoReal["agendar"];
}) {
  const [status, setStatus] = useState<StatusConexao>("ocioso");
  const [reconexoes, setReconexoes] = useState(0);
  const [cliente] = useState(() =>
    typeof window === "undefined"
      ? null
      : new ClienteTempoReal({
          url: urlTempoReal(),
          criarSocket,
          agendar,
          aoMudarStatus: setStatus,
          aoReconectar: () => setReconexoes((n) => n + 1),
          // Handshake recusado chega como 1006: confere a sessão por HTTP (401/402 redirecionam).
          aoFalhasSeguidas: () => void api.eu().catch(() => {}),
          aoSessaoRevogada: irParaLogin,
          aoAssinaturaVencida: () => window.location.assign("/assinatura"),
        }),
  );

  useEffect(() => {
    cliente?.retomar();
    return () => cliente?.fechar();
  }, [cliente]);

  return <Contexto.Provider value={{ cliente, status, reconexoes }}>{children}</Contexto.Provider>;
}

export function useStatusTempoReal(): StatusConexao {
  return useContext(Contexto).status;
}

export function useReconexoes(): number {
  return useContext(Contexto).reconexoes;
}

/** Assina um canal enquanto o componente estiver montado (null = nenhum). */
export function useCanal<C extends Canal>(canal: C | null, ouvinte: (dados: DadosDoCanal<C>) => void): void {
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
