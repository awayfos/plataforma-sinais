"use client";

import { useId, useState } from "react";
import type { Modo } from "@/lib/api/tipos";
import { useSessao } from "./ProvedorSessao";

const OPCOES: { valor: Modo; rotulo: string; dica: string }[] = [
  { valor: "essencial", rotulo: "Essencial", dica: "O essencial para decidir, sem excesso de números." },
  { valor: "avancado", rotulo: "Avançado", dica: "Todos os indicadores, painéis RSI e MACD e detalhes da estrutura." },
];

export function AlternadorModo() {
  const { usuario, definirModo } = useSessao();
  const [erro, setErro] = useState(false);
  const nome = useId();
  const atual = usuario?.modo;

  return (
    <fieldset className="relative flex w-fit items-center rounded-md border border-borda bg-fundo p-0.5" disabled={!usuario}>
      <legend className="sr-only">Modo de exibição</legend>
      {OPCOES.map((o) => (
        <label
          key={o.valor}
          title={o.dica}
          className={`cursor-pointer rounded px-2.5 py-1 text-xs font-medium transition-colors has-[:focus-visible]:ring-1 has-[:focus-visible]:ring-ouro ${
            atual === o.valor ? "bg-painel-2 text-texto shadow-sm" : "text-apagado hover:text-suave"
          }`}
        >
          <input
            type="radio"
            name={nome}
            value={o.valor}
            checked={atual === o.valor}
            onChange={() => {
              setErro(false);
              definirModo(o.valor).catch(() => setErro(true));
            }}
            className="sr-only"
          />
          {o.rotulo}
        </label>
      ))}
      {erro && (
        <span role="alert" className="absolute top-full right-0 mt-1 text-[11px] whitespace-nowrap text-baixa">
          Não foi possível salvar o modo.
        </span>
      )}
    </fieldset>
  );
}
