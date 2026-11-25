"use client";

import { useState, type FormEvent } from "react";
import { ErroApi } from "@/lib/api/cliente";
import { api } from "@/lib/api/endpoints";
import type { Id, Plano, StatusUsuario, UsuarioAdmin } from "@/lib/api/tipos";
import { formatarData } from "@/lib/formato";
import { usarDados } from "@/lib/usarDados";
import { Carregando, ErroEstado, Vazio } from "@/components/ui/Estado";
import { botao, campo, painel, rotulo, tabela } from "@/components/ui/estilos";
import { EMAIL_VALIDO, dataParaMs, msParaData } from "./util";

const COR_STATUS: Record<StatusUsuario, string> = {
  ativo: "text-alta border-alta/30 bg-alta/10",
  bloqueado: "text-baixa border-baixa/30 bg-baixa/10",
  desativado: "text-apagado border-borda bg-painel-2",
};

const SENHA_MINIMA = 10;

function FormNovoUsuario({ planos, aoCriar, aoCancelar }: { planos: Plano[]; aoCriar: () => void; aoCancelar: () => void }) {
  const [email, setEmail] = useState("");
  const [nome, setNome] = useState("");
  const [senha, setSenha] = useState("");
  const [plano, setPlano] = useState<string>(planos[0] ? String(planos[0].id) : "");
  const [vence, setVence] = useState(() => msParaData(Date.now() + 30 * 86_400_000));
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setErro(null);
    if (!EMAIL_VALIDO.test(email.trim())) return setErro("Informe um e-mail válido.");
    if (!nome.trim()) return setErro("Informe o nome.");
    if (senha.length < SENHA_MINIMA) return setErro(`A senha temporária precisa ter pelo menos ${SENHA_MINIMA} caracteres.`);
    const planoEscolhido = planos.find((p) => String(p.id) === plano) ?? (plano === "" ? planos[0] : undefined);
    if (!planoEscolhido) return setErro("Escolha um plano.");
    if (!vence) return setErro("Informe o vencimento.");
    setEnviando(true);
    try {
      await api.admin.criarUsuario({
        email: email.trim(),
        nome: nome.trim(),
        senha_temporaria: senha,
        plano: planoEscolhido.id,
        vence_em: dataParaMs(vence, true),
      });
      aoCriar();
    } catch (err) {
      setErro(err instanceof ErroApi ? err.message : "Não foi possível criar o usuário.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form aria-label="Novo usuário" onSubmit={enviar} noValidate className={`${painel} grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-5`}>
      <div>
        <label htmlFor="nu-email" className={rotulo}>E-mail</label>
        <input id="nu-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} className={campo} autoComplete="off" />
      </div>
      <div>
        <label htmlFor="nu-nome" className={rotulo}>Nome</label>
        <input id="nu-nome" value={nome} onChange={(e) => setNome(e.target.value)} className={campo} autoComplete="off" />
      </div>
      <div>
        <label htmlFor="nu-senha" className={rotulo}>Senha temporária</label>
        <input id="nu-senha" type="text" value={senha} onChange={(e) => setSenha(e.target.value)} className={`${campo} num`} autoComplete="off" />
      </div>
      <div>
        <label htmlFor="nu-plano" className={rotulo}>Plano</label>
        <select id="nu-plano" value={plano || (planos[0] ? String(planos[0].id) : "")} onChange={(e) => setPlano(e.target.value)} className={campo}>
          {planos.length === 0 && <option value="">Nenhum plano cadastrado</option>}
          {planos.map((p) => (
            <option key={String(p.id)} value={String(p.id)}>{p.nome}</option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="nu-vence" className={rotulo}>Vence em</label>
        <input id="nu-vence" type="date" value={vence} onChange={(e) => setVence(e.target.value)} className={campo} />
      </div>
      {erro && (
        <p role="alert" className="text-sm text-baixa sm:col-span-2 lg:col-span-5">{erro}</p>
      )}
      <div className="flex gap-2 sm:col-span-2 lg:col-span-5">
        <button type="submit" className={botao.primario} disabled={enviando}>Criar usuário</button>
        <button type="button" className={botao.secundario} onClick={aoCancelar}>Cancelar</button>
      </div>
    </form>
  );
}

function LinhaUsuario({ u, planos, aoMudar }: { u: UsuarioAdmin; planos: Plano[]; aoMudar: () => void }) {
  const [acao, setAcao] = useState<"nenhuma" | "bloquear" | "editar" | "renovar">("nenhuma");
  const [nome, setNome] = useState(u.nome);
  const [email, setEmail] = useState(u.email);
  const [plano, setPlano] = useState(planos[0] ? String(planos[0].id) : "");
  const [fim, setFim] = useState(() => msParaData(Math.max(Date.now(), u.assinatura?.vence_em ?? 0) + 30 * 86_400_000));
  const [erro, setErro] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  async function executar(fn: () => Promise<unknown>) {
    setErro(null);
    setOcupado(true);
    try {
      await fn();
      setAcao("nenhuma");
      aoMudar();
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Falha na operação.");
    } finally {
      setOcupado(false);
    }
  }

  const status = u.status ?? "ativo";
  return (
    <tr className={tabela.linha}>
      <td className={tabela.td}>
        {acao === "editar" ? (
          <input aria-label="Nome" value={nome} onChange={(e) => setNome(e.target.value)} className={`${campo} py-1`} />
        ) : (
          <span className="font-medium">{u.nome}</span>
        )}
      </td>
      <td className={`${tabela.td} text-suave`}>
        {acao === "editar" ? (
          <input aria-label="E-mail" type="email" value={email} onChange={(e) => setEmail(e.target.value)} className={`${campo} py-1`} />
        ) : (
          u.email
        )}
      </td>
      <td className={tabela.td}>
        <span className={`rounded border px-1.5 py-0.5 text-[11px] font-medium capitalize ${COR_STATUS[status]}`}>{status}</span>
        {u.papel === "admin" && <span className="ml-1.5 text-[11px] text-ouro">admin</span>}
      </td>
      <td className={`${tabela.td} text-suave`}>{u.assinatura?.plano ?? "—"}</td>
      <td className={`${tabela.td} num text-suave`}>
        {formatarData(u.assinatura?.vence_em ?? null)}
        {u.assinatura && u.assinatura.status !== "ativa" && <span className="ml-1 text-[11px] text-alerta">({u.assinatura.status})</span>}
      </td>
      <td className={`${tabela.td} text-right`}>
        <div className="flex flex-wrap justify-end gap-1.5">
          {acao === "nenhuma" && (
            <>
              <button type="button" className={botao.fantasma} onClick={() => setAcao("editar")} aria-label={`Editar ${u.nome}`}>Editar</button>
              <button type="button" className={botao.fantasma} onClick={() => setAcao("renovar")} aria-label={`Renovar ${u.nome}`}>Renovar</button>
              {status === "bloqueado" ? (
                <button type="button" className={botao.fantasma} disabled={ocupado} onClick={() => executar(() => api.admin.editarUsuario(u.id, { status: "ativo" }))}>
                  Desbloquear
                </button>
              ) : (
                <button type="button" className={botao.fantasma} onClick={() => setAcao("bloquear")} aria-label={`Bloquear ${u.nome}`}>Bloquear</button>
              )}
            </>
          )}
          {acao === "bloquear" && (
            <>
              <span className="self-center text-[11px] text-suave">Bloquear acesso agora?</span>
              <button type="button" className={botao.perigo} disabled={ocupado} onClick={() => executar(() => api.admin.editarUsuario(u.id, { status: "bloqueado" }))}>
                Confirmar bloqueio
              </button>
              <button type="button" className={botao.fantasma} onClick={() => setAcao("nenhuma")}>Cancelar</button>
            </>
          )}
          {acao === "editar" && (
            <>
              <button
                type="button"
                className={botao.secundario}
                disabled={ocupado}
                onClick={() => {
                  if (!EMAIL_VALIDO.test(email.trim()) || !nome.trim()) return setErro("Nome e e-mail válidos são obrigatórios.");
                  void executar(() => api.admin.editarUsuario(u.id, { nome: nome.trim(), email: email.trim() }));
                }}
              >
                Salvar
              </button>
              <button type="button" className={botao.fantasma} onClick={() => setAcao("nenhuma")}>Cancelar</button>
            </>
          )}
          {acao === "renovar" && (
            <>
              <select aria-label="Plano" value={plano || (planos[0] ? String(planos[0].id) : "")} onChange={(e) => setPlano(e.target.value)} className={`${campo} w-32 py-1`}>
                {planos.map((p) => (
                  <option key={String(p.id)} value={String(p.id)}>{p.nome}</option>
                ))}
              </select>
              <input aria-label="Novo vencimento" type="date" value={fim} onChange={(e) => setFim(e.target.value)} className={`${campo} w-40 py-1`} />
              <button
                type="button"
                className={botao.secundario}
                disabled={ocupado || planos.length === 0}
                onClick={() => {
                  const p = planos.find((x) => String(x.id) === plano) ?? (plano === "" ? planos[0] : undefined);
                  if (!p) return setErro("Escolha um plano.");
                  void executar(() =>
                    api.admin.salvarAssinatura({ usuario_id: u.id as Id, plano_id: p.id, inicio: Date.now(), fim: dataParaMs(fim, true) }),
                  );
                }}
              >
                Renovar
              </button>
              <button type="button" className={botao.fantasma} onClick={() => setAcao("nenhuma")}>Cancelar</button>
            </>
          )}
        </div>
        {erro && <p role="alert" className="mt-1 text-[11px] text-baixa">{erro}</p>}
      </td>
    </tr>
  );
}

export function GestaoUsuarios() {
  const [texto, setTexto] = useState("");
  const [status, setStatus] = useState("");
  const [consulta, setConsulta] = useState({ busca: "", status: "" });
  const [criando, setCriando] = useState(false);

  const usuarios = usarDados(`usuarios:${consulta.busca}:${consulta.status}`, (s) =>
    api.admin.usuarios({ busca: consulta.busca || undefined, status: consulta.status || undefined }, s),
  );
  const planos = usarDados("planos", (s) => api.admin.planos(s));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <form
          role="search"
          className="flex flex-wrap items-end gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            setConsulta({ busca: texto.trim(), status });
          }}
        >
          <input
            type="search"
            aria-label="Buscar usuários"
            placeholder="Nome ou e-mail"
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            className={`${campo} w-64`}
          />
          <select
            aria-label="Status"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setConsulta({ busca: texto.trim(), status: e.target.value });
            }}
            className={`${campo} w-36`}
          >
            <option value="">Todos</option>
            <option value="ativo">Ativos</option>
            <option value="bloqueado">Bloqueados</option>
            <option value="desativado">Desativados</option>
          </select>
          <button type="submit" className={botao.secundario}>Buscar</button>
        </form>
        <button type="button" className={`${botao.primario} ml-auto`} onClick={() => setCriando(true)} disabled={criando}>
          Novo usuário
        </button>
      </div>

      {criando && (
        <FormNovoUsuario
          planos={planos.dados ?? []}
          aoCancelar={() => setCriando(false)}
          aoCriar={() => {
            setCriando(false);
            usuarios.recarregar();
          }}
        />
      )}

      <section className={`${painel} overflow-x-auto p-1`}>
        {usuarios.erro ? (
          <div className="p-3"><ErroEstado mensagem={usuarios.erro.message} aoTentarDeNovo={usuarios.recarregar} /></div>
        ) : !usuarios.dados ? (
          <div className="p-3"><Carregando rotulo="Carregando usuários…" /></div>
        ) : usuarios.dados.length === 0 ? (
          <div className="p-3"><Vazio titulo="Nenhum usuário encontrado" /></div>
        ) : (
          <table className={tabela.raiz}>
            <caption className="sr-only">Usuários</caption>
            <thead className={tabela.cabeca}>
              <tr>
                <th scope="col" className={tabela.th}>Nome</th>
                <th scope="col" className={tabela.th}>E-mail</th>
                <th scope="col" className={tabela.th}>Status</th>
                <th scope="col" className={tabela.th}>Plano</th>
                <th scope="col" className={tabela.th}>Vence em</th>
                <th scope="col" className={`${tabela.th} text-right`}>Ações</th>
              </tr>
            </thead>
            <tbody>
              {usuarios.dados.map((u) => (
                <LinhaUsuario key={String(u.id)} u={u} planos={planos.dados ?? []} aoMudar={usuarios.recarregar} />
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
