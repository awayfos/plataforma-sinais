"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ErroApi } from "@/lib/api/cliente";
import { api } from "@/lib/api/endpoints";
import type { Usuario } from "@/lib/api/tipos";
import { formatarData } from "@/lib/formato";
import { AvisoRisco } from "@/components/ui/AvisoRisco";
import { Marca } from "@/components/ui/Marca";
import { botao } from "@/components/ui/estilos";

type Situacao = { tipo: "carregando" } | { tipo: "usuario"; usuario: Usuario } | { tipo: "sem_sessao" } | { tipo: "desconhecida" };

const TEXTO_STATUS = { ativa: "ativa", vencida: "vencida", bloqueada: "bloqueada" } as const;

export function TelaAssinatura() {
  const [situacao, setSituacao] = useState<Situacao>({ tipo: "carregando" });

  useEffect(() => {
    let vivo = true;
    api.eu({ semRedirecionar: true }).then(
      (usuario) => vivo && setSituacao({ tipo: "usuario", usuario }),
      (e: unknown) => vivo && setSituacao({ tipo: e instanceof ErroApi && e.status === 401 ? "sem_sessao" : "desconhecida" }),
    );
    return () => {
      vivo = false;
    };
  }, []);

  async function sair() {
    try {
      await api.logout();
    } finally {
      window.location.assign("/login");
    }
  }

  const assinatura = situacao.tipo === "usuario" ? situacao.usuario.assinatura : null;

  return (
    <div className="flex min-h-dvh flex-col">
      <main className="flex flex-1 items-center justify-center px-6 py-12">
        <div className="w-full max-w-md rounded-xl border border-borda bg-painel p-8">
          <Marca />
          <h1 className="mt-8 text-xl font-semibold tracking-tight">Sua assinatura não está ativa</h1>
          <p className="mt-2 text-sm leading-relaxed text-suave">
            O acesso ao terminal, às análises e aos sinais exige uma assinatura ativa. Para renovar, fale com o suporte
            ou com quem administra sua conta.
          </p>

          {situacao.tipo === "carregando" && <p className="mt-6 text-sm text-apagado" role="status">Verificando sua conta…</p>}
          {assinatura && (
            <dl className="mt-6 grid grid-cols-2 gap-3 rounded-md border border-borda bg-fundo p-4 text-sm">
              <dt className="text-apagado">Plano</dt>
              <dd className="text-right">{assinatura.plano ?? "Sem plano"}</dd>
              <dt className="text-apagado">Situação</dt>
              <dd className="text-right font-medium text-alerta">{TEXTO_STATUS[assinatura.status]}</dd>
              <dt className="text-apagado">Vencimento</dt>
              <dd className="num text-right">{formatarData(assinatura.vence_em)}</dd>
            </dl>
          )}

          <div className="mt-8 flex flex-wrap gap-3">
            {situacao.tipo === "usuario" && assinatura?.status === "ativa" ? (
              <Link href="/terminal" className={botao.primario}>
                Ir para o terminal
              </Link>
            ) : null}
            {situacao.tipo === "sem_sessao" ? (
              <Link href="/login" className={botao.primario}>
                Entrar
              </Link>
            ) : (
              <button type="button" onClick={() => void sair()} className={botao.secundario}>
                Sair
              </button>
            )}
          </div>
        </div>
      </main>
      <AvisoRisco />
    </div>
  );
}
