"use client";

import { useState, type FormEvent } from "react";
import { ErroApi } from "@/lib/api/cliente";
import { api } from "@/lib/api/endpoints";
import { EXPIRACOES, type Plano } from "@/lib/api/tipos";
import { formatarMoeda } from "@/lib/formato";
import { ROTULO_EXPIRACAO } from "@/lib/sinais";
import { useDados } from "@/lib/useDados";
import { Carregando, ErroEstado, Vazio } from "@/components/ui/Estado";
import { botao, campo, painel, rotulo, tabela } from "@/components/ui/estilos";

type Rascunho = Omit<Plano, "id"> & { id?: Plano["id"] };

const VAZIO: Rascunho = {
  nome: "",
  duracao_dias: 30,
  preco_centavos: 0,
  recursos: { ativos: [], expiracoes: [], modo_avancado: false, cursos: false },
  ativo: true,
};

function FormPlano({ inicial, simbolos, aoSalvar, aoCancelar }: { inicial: Rascunho; simbolos: string[]; aoSalvar: () => void; aoCancelar: () => void }) {
  const [r, setR] = useState<Rascunho>(inicial);
  const [preco, setPreco] = useState(() => (inicial.preco_centavos / 100).toFixed(2).replace(".", ","));
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const alternar = (lista: string[], v: string) => (lista.includes(v) ? lista.filter((x) => x !== v) : [...lista, v]);

  async function enviar(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setErro(null);
    const centavos = Math.round(Number(preco.replace(/\./g, "").replace(",", ".")) * 100);
    if (!r.nome.trim()) return setErro("Informe o nome do plano.");
    if (!Number.isInteger(r.duracao_dias) || r.duracao_dias < 1) return setErro("A duração deve ser de pelo menos 1 dia.");
    if (!Number.isFinite(centavos) || centavos < 0) return setErro("Preço inválido.");
    setEnviando(true);
    try {
      const dados = { ...r, nome: r.nome.trim(), preco_centavos: centavos };
      if (r.id !== undefined) await api.admin.editarPlano({ ...dados, id: r.id });
      else await api.admin.criarPlano(dados);
      aoSalvar();
    } catch (err) {
      setErro(err instanceof ErroApi ? err.message : "Não foi possível salvar o plano.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form aria-label={r.id !== undefined ? "Editar plano" : "Novo plano"} onSubmit={enviar} noValidate className={`${painel} space-y-4 p-4`}>
      <div className="grid gap-3 sm:grid-cols-3">
        <div>
          <label htmlFor="pl-nome" className={rotulo}>Nome</label>
          <input id="pl-nome" value={r.nome} onChange={(e) => setR({ ...r, nome: e.target.value })} className={campo} />
        </div>
        <div>
          <label htmlFor="pl-dur" className={rotulo}>Duração (dias)</label>
          <input id="pl-dur" type="number" min={1} value={r.duracao_dias} onChange={(e) => setR({ ...r, duracao_dias: Number(e.target.value) })} className={`${campo} num`} />
        </div>
        <div>
          <label htmlFor="pl-preco" className={rotulo}>Preço (R$)</label>
          <input id="pl-preco" inputMode="decimal" value={preco} onChange={(e) => setPreco(e.target.value)} className={`${campo} num`} />
        </div>
      </div>
      <fieldset>
        <legend className={rotulo}>Ativos liberados</legend>
        <div className="flex flex-wrap gap-3">
          {simbolos.map((s) => (
            <label key={s} className="flex items-center gap-1.5 text-sm text-suave">
              <input type="checkbox" checked={r.recursos.ativos.includes(s)} onChange={() => setR({ ...r, recursos: { ...r.recursos, ativos: alternar(r.recursos.ativos, s) } })} />
              <span className="num">{s}</span>
            </label>
          ))}
        </div>
      </fieldset>
      <fieldset>
        <legend className={rotulo}>Expirações liberadas</legend>
        <div className="flex flex-wrap gap-3">
          {EXPIRACOES.map((x) => (
            <label key={x} className="flex items-center gap-1.5 text-sm text-suave">
              <input type="checkbox" checked={r.recursos.expiracoes.includes(x)} onChange={() => setR({ ...r, recursos: { ...r.recursos, expiracoes: alternar(r.recursos.expiracoes, x) } })} />
              {ROTULO_EXPIRACAO[x]}
            </label>
          ))}
        </div>
      </fieldset>
      <div className="flex flex-wrap gap-4 text-sm text-suave">
        <label className="flex items-center gap-1.5">
          <input type="checkbox" checked={r.recursos.modo_avancado} onChange={(e) => setR({ ...r, recursos: { ...r.recursos, modo_avancado: e.target.checked } })} />
          Modo Avançado
        </label>
        <label className="flex items-center gap-1.5">
          <input type="checkbox" checked={r.recursos.cursos} onChange={(e) => setR({ ...r, recursos: { ...r.recursos, cursos: e.target.checked } })} />
          Cursos
        </label>
        <label className="flex items-center gap-1.5">
          <input type="checkbox" checked={r.ativo} onChange={(e) => setR({ ...r, ativo: e.target.checked })} />
          Plano ativo (disponível para novas assinaturas)
        </label>
      </div>
      {erro && <p role="alert" className="text-sm text-baixa">{erro}</p>}
      <div className="flex gap-2">
        <button type="submit" className={botao.primario} disabled={enviando}>Salvar plano</button>
        <button type="button" className={botao.secundario} onClick={aoCancelar}>Cancelar</button>
      </div>
    </form>
  );
}

export function GestaoPlanos() {
  const planos = useDados("planos", (s) => api.admin.planos(s));
  const ativos = useDados("ativos", (s) => api.ativos(s));
  const [editando, setEditando] = useState<Rascunho | null>(null);
  const simbolos = (ativos.dados ?? []).map((a) => a.simbolo);

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button type="button" className={botao.primario} onClick={() => setEditando(VAZIO)} disabled={editando !== null}>Novo plano</button>
      </div>
      {editando && (
        <FormPlano
          key={String(editando.id ?? "novo")}
          inicial={editando}
          simbolos={simbolos}
          aoCancelar={() => setEditando(null)}
          aoSalvar={() => {
            setEditando(null);
            planos.recarregar();
          }}
        />
      )}
      <section className={`${painel} overflow-x-auto p-1`}>
        {planos.erro ? (
          <div className="p-3"><ErroEstado mensagem={planos.erro.message} aoTentarDeNovo={planos.recarregar} /></div>
        ) : !planos.dados ? (
          <div className="p-3"><Carregando /></div>
        ) : planos.dados.length === 0 ? (
          <div className="p-3"><Vazio titulo="Nenhum plano cadastrado" /></div>
        ) : (
          <table className={tabela.raiz}>
            <caption className="sr-only">Planos</caption>
            <thead className={tabela.cabeca}>
              <tr>
                <th scope="col" className={tabela.th}>Nome</th>
                <th scope="col" className={tabela.th}>Duração</th>
                <th scope="col" className={tabela.th}>Preço</th>
                <th scope="col" className={tabela.th}>Recursos</th>
                <th scope="col" className={tabela.th}>Situação</th>
                <th scope="col" className={`${tabela.th} text-right`}>Ações</th>
              </tr>
            </thead>
            <tbody>
              {planos.dados.map((p) => (
                <tr key={String(p.id)} className={tabela.linha}>
                  <td className={`${tabela.td} font-medium`}>{p.nome}</td>
                  <td className={`${tabela.td} num text-suave`}>{p.duracao_dias} dias</td>
                  <td className={`${tabela.td} num`}>{formatarMoeda(p.preco_centavos)}</td>
                  <td className={`${tabela.td} text-[12px] text-suave`}>
                    {p.recursos.ativos.join(", ") || "—"} · {p.recursos.expiracoes.join(", ") || "—"}
                    {p.recursos.modo_avancado && " · Avançado"}
                    {p.recursos.cursos && " · Cursos"}
                  </td>
                  <td className={`${tabela.td} text-[12px]`}>{p.ativo ? <span className="text-alta">Ativo</span> : <span className="text-apagado">Inativo</span>}</td>
                  <td className={`${tabela.td} text-right`}>
                    <button type="button" className={botao.fantasma} onClick={() => setEditando(p)} aria-label={`Editar plano ${p.nome}`}>Editar</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
