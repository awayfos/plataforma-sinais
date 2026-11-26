"use client";

import Link from "next/link";
import { useSessao } from "@/components/sessao/ProvedorSessao";
import { AlternadorModo } from "@/components/sessao/AlternadorModo";
import { Carregando, ErroEstado } from "@/components/ui/Estado";
import { painel, tituloPainel } from "@/components/ui/estilos";
import { api } from "@/lib/api/endpoints";
import { diasAte, formatarData, formatarPercentual, periodoAteAgora } from "@/lib/formato";
import { estatisticas } from "@/lib/sinais";
import { useDados } from "@/lib/useDados";
import { FormSenha } from "./FormSenha";

const COR_STATUS = { ativa: "text-alta", vencida: "text-alerta", bloqueada: "text-baixa" } as const;

function ResumoHistorico() {
  const { dados, erro, carregando, recarregar } = useDados("historico-30d", (sinal) =>
    api.historico(periodoAteAgora(30), sinal),
  );
  if (carregando) return <Carregando linhas={2} />;
  if (erro) return <ErroEstado mensagem={erro.message} aoTentarDeNovo={recarregar} />;
  const s = estatisticas(dados ?? []);
  return (
    <div>
      <dl className="grid grid-cols-3 gap-3 text-center">
        <div className="rounded-md bg-fundo p-3">
          <dt className="text-[11px] text-apagado">Sinais liquidados</dt>
          <dd className="num mt-1 text-lg">{s.n}</dd>
        </div>
        <div className="rounded-md bg-fundo p-3">
          <dt className="text-[11px] text-apagado">Taxa de acerto</dt>
          <dd className="num mt-1 text-lg">{formatarPercentual(s.taxa)}</dd>
        </div>
        <div className="rounded-md bg-fundo p-3">
          <dt className="text-[11px] text-apagado">Empates</dt>
          <dd className="num mt-1 text-lg">{s.tie}</dd>
        </div>
      </dl>
      <p className="mt-3 text-xs text-apagado">
        Últimos 30 dias, todos os ativos.{" "}
        <Link href="/historico" className="text-ouro underline-offset-2 hover:underline">
          Ver histórico completo
        </Link>
      </p>
    </div>
  );
}

export function Perfil() {
  const { usuario, carregando, erro, atualizar } = useSessao();

  return (
    <main className="mx-auto w-full max-w-5xl space-y-4 px-4 py-6">
      <h1 className="text-lg font-semibold tracking-tight">Perfil</h1>
      {carregando && <Carregando />}
      {erro && !usuario && <ErroEstado mensagem={erro.message} aoTentarDeNovo={() => void atualizar()} />}
      {usuario && (
        <div className="grid gap-4 md:grid-cols-2">
          <section className={`${painel} p-5`} aria-labelledby="t-conta">
            <h2 id="t-conta" className={tituloPainel}>
              Conta
            </h2>
            <dl className="mt-4 space-y-2 text-sm">
              <div className="flex justify-between gap-4">
                <dt className="text-apagado">Nome</dt>
                <dd>{usuario.nome}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-apagado">E-mail</dt>
                <dd className="truncate">{usuario.email}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-apagado">Perfil</dt>
                <dd>{usuario.papel === "admin" ? "Administrador" : "Cliente"}</dd>
              </div>
            </dl>
          </section>

          <section className={`${painel} p-5`} aria-labelledby="t-assinatura">
            <h2 id="t-assinatura" className={tituloPainel}>
              Assinatura
            </h2>
            <dl className="mt-4 space-y-2 text-sm">
              <div className="flex justify-between gap-4">
                <dt className="text-apagado">Plano</dt>
                <dd data-testid="perfil-plano">{usuario.assinatura.plano ?? "Sem plano"}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-apagado">Situação</dt>
                <dd className={`font-medium capitalize ${COR_STATUS[usuario.assinatura.status]}`}>{usuario.assinatura.status}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-apagado">Vence em</dt>
                <dd className="num">
                  {formatarData(usuario.assinatura.vence_em)}
                  {usuario.assinatura.vence_em !== null && usuario.assinatura.status === "ativa" && (
                    <span className="ml-2 text-xs text-apagado">({Math.max(0, diasAte(usuario.assinatura.vence_em))} dias)</span>
                  )}
                </dd>
              </div>
            </dl>
          </section>

          <section className={`${painel} p-5`} aria-labelledby="t-pref">
            <h2 id="t-pref" className={tituloPainel}>
              Modo de exibição
            </h2>
            <p className="mt-3 mb-4 text-sm leading-relaxed text-suave">
              <strong className="font-medium text-texto">Essencial</strong> mostra o necessário para decidir.{" "}
              <strong className="font-medium text-texto">Avançado</strong> abre todos os indicadores, os painéis RSI e MACD e
              os detalhes da estrutura.
            </p>
            <AlternadorModo />
          </section>

          <section className={`${painel} p-5`} aria-labelledby="t-hist">
            <h2 id="t-hist" className={`${tituloPainel} mb-4`}>
              Seu histórico de sinais
            </h2>
            <ResumoHistorico />
          </section>

          <section className={`${painel} p-5 md:col-span-2`} aria-labelledby="t-senha">
            <h2 id="t-senha" className={`${tituloPainel} mb-4`}>
              Trocar senha
            </h2>
            <FormSenha />
          </section>
        </div>
      )}
    </main>
  );
}
