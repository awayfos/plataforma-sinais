"use client";

import { useState } from "react";
import { api } from "@/lib/api/endpoints";
import { formatarDataHora } from "@/lib/formato";
import { useDados } from "@/lib/useDados";
import { Carregando, ErroEstado, Vazio } from "@/components/ui/Estado";
import { botao, campoBase, painel, tabela } from "@/components/ui/estilos";
import { json } from "./util";

function Detalhes({ valor, rotulo }: { valor: unknown; rotulo: string }) {
  if (valor === undefined || valor === null) return <span className="text-apagado">—</span>;
  return (
    <details>
      <summary className="cursor-pointer text-[12px] text-suave hover:text-texto">{rotulo}</summary>
      <pre className="num mt-1 max-h-48 max-w-md overflow-auto rounded bg-fundo p-2 text-[11px] text-suave">{json(valor)}</pre>
    </details>
  );
}

function Moldura({ children }: { children: React.ReactNode }) {
  return <section className={`${painel} overflow-x-auto p-1`}>{children}</section>;
}

export function LogAcessos() {
  const [texto, setTexto] = useState("");
  const [usuarioId, setUsuarioId] = useState("");
  const q = useDados(`acessos:${usuarioId}`, (s) => api.admin.acessos({ usuario_id: usuarioId || undefined }, s));
  return (
    <div className="space-y-4">
      <form
        role="search"
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          setUsuarioId(texto.trim());
        }}
      >
        <input type="search" aria-label="Filtrar por ID do usuário" placeholder="ID do usuário" value={texto} onChange={(e) => setTexto(e.target.value)} className={`${campoBase} num w-48 py-2`} />
        <button type="submit" className={botao.secundario}>Filtrar</button>
      </form>
      <Moldura>
        {q.erro ? (
          <div className="p-3"><ErroEstado mensagem={q.erro.message} aoTentarDeNovo={q.recarregar} /></div>
        ) : !q.dados ? (
          <div className="p-3"><Carregando /></div>
        ) : q.dados.length === 0 ? (
          <div className="p-3"><Vazio titulo="Nenhum acesso registrado" /></div>
        ) : (
          <table className={tabela.raiz}>
            <caption className="sr-only">Log de acesso</caption>
            <thead className={tabela.cabeca}>
              <tr>
                <th scope="col" className={tabela.th}>Quando</th>
                <th scope="col" className={tabela.th}>Usuário</th>
                <th scope="col" className={tabela.th}>Evento</th>
                <th scope="col" className={tabela.th}>IP</th>
                <th scope="col" className={tabela.th}>Navegador</th>
              </tr>
            </thead>
            <tbody>
              {q.dados.map((a, i) => (
                <tr key={String(a.id ?? i)} className={tabela.linha}>
                  <td className={`${tabela.td} num text-[13px] text-suave`}>{formatarDataHora(a.ts)}</td>
                  <td className={`${tabela.td} text-[13px]`}>{a.email ?? (a.usuario_id !== undefined ? `#${a.usuario_id}` : "—")}</td>
                  <td className={`${tabela.td} text-[13px]`}>{a.evento}</td>
                  <td className={`${tabela.td} num text-[13px] text-suave`}>{a.ip ?? "—"}</td>
                  <td className={`${tabela.td} max-w-xs truncate text-[12px] text-apagado`} title={a.user_agent ?? undefined}>{a.user_agent ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Moldura>
    </div>
  );
}

export function LogAuditoria() {
  const q = useDados("auditoria", (s) => api.admin.auditoria(s));
  return (
    <Moldura>
      {q.erro ? (
        <div className="p-3"><ErroEstado mensagem={q.erro.message} aoTentarDeNovo={q.recarregar} /></div>
      ) : !q.dados ? (
        <div className="p-3"><Carregando /></div>
      ) : q.dados.length === 0 ? (
        <div className="p-3"><Vazio titulo="Nenhuma ação registrada" /></div>
      ) : (
        <table className={tabela.raiz}>
          <caption className="sr-only">Auditoria de ações dos administradores</caption>
          <thead className={tabela.cabeca}>
            <tr>
              <th scope="col" className={tabela.th}>Quando</th>
              <th scope="col" className={tabela.th}>Administrador</th>
              <th scope="col" className={tabela.th}>Ação</th>
              <th scope="col" className={tabela.th}>Alvo</th>
              <th scope="col" className={tabela.th}>Antes</th>
              <th scope="col" className={tabela.th}>Depois</th>
            </tr>
          </thead>
          <tbody>
            {q.dados.map((a, i) => (
              <tr key={String(a.id ?? i)} className={tabela.linha}>
                <td className={`${tabela.td} num text-[13px] text-suave`}>{formatarDataHora(a.ts)}</td>
                <td className={`${tabela.td} text-[13px]`}>{a.admin_email ?? (a.admin_id !== undefined ? `#${a.admin_id}` : "—")}</td>
                <td className={`${tabela.td} text-[13px] font-medium`}>{a.acao}</td>
                <td className={`${tabela.td} text-[13px] text-suave`}>{a.alvo ?? "—"}</td>
                <td className={tabela.td}><Detalhes valor={a.antes} rotulo="Ver" /></td>
                <td className={tabela.td}><Detalhes valor={a.depois} rotulo="Ver" /></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Moldura>
  );
}

export function EventosQualidade() {
  const q = useDados("qualidade", (s) => api.admin.qualidade(s));
  return (
    <div className="space-y-3">
      <p className="max-w-3xl text-xs leading-relaxed text-apagado">
        Gaps, duplicados, atraso e desvio de relógio detectados na coleta. Nessas janelas a análise e os sinais param e a
        decisão volta para AGUARDAR.
      </p>
      <Moldura>
        {q.erro ? (
          <div className="p-3"><ErroEstado mensagem={q.erro.message} aoTentarDeNovo={q.recarregar} /></div>
        ) : !q.dados ? (
          <div className="p-3"><Carregando /></div>
        ) : q.dados.length === 0 ? (
          <div className="p-3"><Vazio titulo="Nenhum evento recente" /></div>
        ) : (
          <table className={tabela.raiz}>
            <caption className="sr-only">Eventos de qualidade de dados</caption>
            <thead className={tabela.cabeca}>
              <tr>
                <th scope="col" className={tabela.th}>Tipo</th>
                <th scope="col" className={tabela.th}>Ativo</th>
                <th scope="col" className={tabela.th}>Início</th>
                <th scope="col" className={tabela.th}>Fim</th>
                <th scope="col" className={tabela.th}>Detalhes</th>
              </tr>
            </thead>
            <tbody>
              {q.dados.map((ev, i) => (
                <tr key={String(ev.id ?? i)} className={tabela.linha}>
                  <td className={`${tabela.td} text-[13px] font-medium text-alerta`}>{ev.tipo}</td>
                  <td className={`${tabela.td} num text-[13px]`}>
                    {ev.simbolo ?? "—"}
                    {ev.intervalo && <span className="ml-1 text-apagado">{ev.intervalo}</span>}
                  </td>
                  <td className={`${tabela.td} num text-[13px] text-suave`}>{formatarDataHora(ev.inicio)}</td>
                  <td className={`${tabela.td} num text-[13px] text-suave`}>{ev.fim ? formatarDataHora(ev.fim) : "em aberto"}</td>
                  <td className={tabela.td}><Detalhes valor={ev.detalhes} rotulo="Ver" /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Moldura>
    </div>
  );
}
