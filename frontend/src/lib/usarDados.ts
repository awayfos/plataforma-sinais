"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ErroApi, paraErroApi } from "./api/cliente";

interface Estado<T> {
  chave: string | null;
  versao: number;
  dados?: T;
  erro?: ErroApi;
}

/**
 * Busca dados para uma chave (null = não buscar). Sem setState síncrono no efeito:
 * "carregando" é derivado de a resposta guardada ser de outra chave/versão.
 */
export function usarDados<T>(chave: string | null, carregar: (sinal: AbortSignal) => Promise<T>) {
  const [estado, setEstado] = useState<Estado<T>>({ chave: null, versao: -1 });
  const [versao, setVersao] = useState(0);
  const carregarRef = useRef(carregar);

  useEffect(() => {
    carregarRef.current = carregar;
  });

  useEffect(() => {
    if (chave === null) return;
    const controle = new AbortController();
    carregarRef.current(controle.signal).then(
      (dados) => {
        if (!controle.signal.aborted) setEstado({ chave, versao, dados });
      },
      (e: unknown) => {
        if (!controle.signal.aborted) setEstado({ chave, versao, erro: paraErroApi(e) });
      },
    );
    return () => controle.abort();
  }, [chave, versao]);

  const recarregar = useCallback(() => setVersao((v) => v + 1), []);
  const mesmaChave = estado.chave === chave;
  return {
    dados: mesmaChave ? estado.dados : undefined,
    erro: mesmaChave && estado.versao === versao ? estado.erro : undefined,
    carregando: chave !== null && !(mesmaChave && estado.versao === versao),
    recarregar,
  };
}
