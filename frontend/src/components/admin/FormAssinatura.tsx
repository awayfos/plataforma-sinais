"use client";

import { useState, type FormEvent } from "react";
import { ErroApi } from "@/lib/api/cliente";
import { api } from "@/lib/api/endpoints";
import { useDados } from "@/lib/useDados";
import { ErroEstado } from "@/components/ui/Estado";
import { botao, campo, painel, rotulo } from "@/components/ui/estilos";
import { dataParaMs, msParaData } from "./util";

export function FormAssinatura() {
  const usuarios = useDados("usuarios-todos", (s) => api.admin.usuarios({}, s));
  const planos = useDados("planos", (s) => api.admin.planos(s));
  const [usuario, setUsuario] = useState("");
  const [plano, setPlano] = useState("");
  const [inicio, setInicio] = useState(() => msParaData(Date.now()));
  const [fim, setFim] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [ok, setOk] = useState(false);
  const [enviando, setEnviando] = useState(false);

  const planoAtual = (planos.dados ?? []).find((p) => String(p.id) === plano);
  const fimSugerido = planoAtual && inicio ? msParaData(dataParaMs(inicio) + planoAtual.duracao_dias * 86_400_000) : "";
  const fimEfetivo = fim || fimSugerido;

  async function enviar(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setErro(null);
    setOk(false);
    const u = (usuarios.dados ?? []).find((x) => String(x.id) === usuario);
    if (!u) return setErro("Escolha o usuário.");
    if (!planoAtual) return setErro("Escolha o plano.");
    if (!inicio || !fimEfetivo) return setErro("Informe início e fim.");
    const msInicio = dataParaMs(inicio);
    const msFim = dataParaMs(fimEfetivo, true);
    if (msFim <= msInicio) return setErro("O fim deve ser depois do início.");
    setEnviando(true);
    try {
      await api.admin.salvarAssinatura({ usuario_id: u.id, plano_id: planoAtual.id, inicio: msInicio, fim: msFim });
      setOk(true);
    } catch (err) {
      setErro(err instanceof ErroApi ? err.message : "Não foi possível salvar a assinatura.");
    } finally {
      setEnviando(false);
    }
  }

  if (usuarios.erro) return <ErroEstado mensagem={usuarios.erro.message} aoTentarDeNovo={usuarios.recarregar} />;

  return (
    <form aria-label="Criar ou renovar assinatura" onSubmit={enviar} noValidate className={`${painel} max-w-2xl space-y-4 p-5`}>
      <p className="text-xs text-apagado">Cria uma assinatura nova ou renova a existente. A verificação de acesso é feita sempre no servidor.</p>
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <label htmlFor="as-usuario" className={rotulo}>Usuário</label>
          <select id="as-usuario" value={usuario} onChange={(e) => setUsuario(e.target.value)} className={campo}>
            <option value="">{usuarios.dados ? "Selecione…" : "Carregando…"}</option>
            {(usuarios.dados ?? []).map((u) => (
              <option key={String(u.id)} value={String(u.id)}>{u.nome} — {u.email}</option>
            ))}
          </select>
        </div>
        <div className="sm:col-span-2">
          <label htmlFor="as-plano" className={rotulo}>Plano</label>
          <select id="as-plano" value={plano} onChange={(e) => setPlano(e.target.value)} className={campo}>
            <option value="">Selecione…</option>
            {(planos.dados ?? []).map((p) => (
              <option key={String(p.id)} value={String(p.id)}>{p.nome} ({p.duracao_dias} dias)</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="as-inicio" className={rotulo}>Início</label>
          <input id="as-inicio" type="date" value={inicio} onChange={(e) => setInicio(e.target.value)} className={campo} />
        </div>
        <div>
          <label htmlFor="as-fim" className={rotulo}>Fim</label>
          <input id="as-fim" type="date" value={fimEfetivo} onChange={(e) => setFim(e.target.value)} className={campo} />
        </div>
      </div>
      {erro && <p role="alert" className="text-sm text-baixa">{erro}</p>}
      {ok && <p role="status" className="text-sm text-alta">Assinatura salva.</p>}
      <button type="submit" className={botao.primario} disabled={enviando}>Salvar assinatura</button>
    </form>
  );
}
