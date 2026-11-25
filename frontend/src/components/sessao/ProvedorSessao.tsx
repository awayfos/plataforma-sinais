"use client";

import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { definirTratadorSessao, ErroApi, paraErroApi } from "@/lib/api/cliente";
import { api } from "@/lib/api/endpoints";
import type { LayoutUsuario, Modo, Usuario } from "@/lib/api/tipos";

interface ValorSessao {
  usuario: Usuario | null;
  erro: ErroApi | null;
  carregando: boolean;
  layout: LayoutUsuario;
  definirModo(modo: Modo): Promise<void>;
  salvarLayout(parcial: Partial<LayoutUsuario>): Promise<void>;
  atualizar(): Promise<void>;
  sair(): Promise<void>;
}

const Contexto = createContext<ValorSessao | null>(null);

const chaveLocal = (id: Usuario["id"]) => `sinais:layout:${id}`;

function lerLayoutLocal(id: Usuario["id"]): LayoutUsuario {
  try {
    const bruto = window.localStorage.getItem(chaveLocal(id));
    return bruto ? (JSON.parse(bruto) as LayoutUsuario) : {};
  } catch {
    return {};
  }
}

export function irParaLogin() {
  const atual = `${window.location.pathname}${window.location.search}`;
  window.location.assign(`/login?proximo=${encodeURIComponent(atual)}`);
}

export function ProvedorSessao({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [erro, setErro] = useState<ErroApi | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [layout, setLayout] = useState<LayoutUsuario>({});

  useEffect(() => {
    definirTratadorSessao({
      aoNaoAutenticado: irParaLogin,
      aoAssinaturaVencida: () => router.replace("/assinatura"),
    });
  }, [router]);

  const atualizar = useCallback(async () => {
    try {
      const u = await api.eu();
      setUsuario(u);
      setLayout(u.layout ?? lerLayoutLocal(u.id));
      setErro(null);
    } catch (e) {
      setErro(paraErroApi(e));
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    let vivo = true;
    api.eu().then(
      (u) => {
        if (!vivo) return;
        setUsuario(u);
        setLayout(u.layout ?? lerLayoutLocal(u.id));
        setCarregando(false);
      },
      (e: unknown) => {
        if (!vivo) return;
        setErro(paraErroApi(e));
        setCarregando(false);
      },
    );
    return () => {
      vivo = false;
    };
  }, []);

  const definirModo = useCallback(async (modo: Modo) => {
    let anterior: Modo | undefined;
    setUsuario((u) => {
      anterior = u?.modo;
      return u ? { ...u, modo } : u;
    });
    try {
      const novo = await api.salvarPreferencias({ modo });
      setUsuario((u) => (u ? { ...u, ...novo, layout: u.layout } : novo));
    } catch (e) {
      setUsuario((u) => (u && anterior ? { ...u, modo: anterior } : u));
      throw e;
    }
  }, []);

  const salvarLayout = useCallback(
    async (parcial: Partial<LayoutUsuario>) => {
      const novo = { ...layout, ...parcial };
      setLayout(novo);
      if (usuario) {
        try {
          window.localStorage.setItem(chaveLocal(usuario.id), JSON.stringify(novo));
        } catch {
          // armazenamento indisponível: segue só com o servidor
        }
      }
      await api.salvarPreferencias({ layout: novo });
    },
    [layout, usuario],
  );

  const sair = useCallback(async () => {
    try {
      await api.logout();
    } finally {
      window.location.assign("/login");
    }
  }, []);

  const valor = useMemo(
    () => ({ usuario, erro, carregando, layout, definirModo, salvarLayout, atualizar, sair }),
    [usuario, erro, carregando, layout, definirModo, salvarLayout, atualizar, sair],
  );

  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useSessao(): ValorSessao {
  const v = useContext(Contexto);
  if (!v) throw new Error("useSessao fora do ProvedorSessao");
  return v;
}
