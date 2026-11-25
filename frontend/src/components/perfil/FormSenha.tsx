"use client";

import { useState, type FormEvent } from "react";
import { ErroApi } from "@/lib/api/cliente";
import { api } from "@/lib/api/endpoints";
import { botao, campo, rotulo } from "@/components/ui/estilos";

const MINIMO = 10;

export function FormSenha() {
  const [atual, setAtual] = useState("");
  const [nova, setNova] = useState("");
  const [confirmacao, setConfirmacao] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [sucesso, setSucesso] = useState(false);
  const [enviando, setEnviando] = useState(false);

  async function enviar(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setErro(null);
    setSucesso(false);
    if (nova.length < MINIMO) return setErro(`A nova senha precisa ter pelo menos ${MINIMO} caracteres.`);
    if (nova !== confirmacao) return setErro("As senhas não coincidem.");
    setEnviando(true);
    try {
      await api.trocarSenha({ senha_atual: atual, senha_nova: nova });
      setSucesso(true);
      setAtual("");
      setNova("");
      setConfirmacao("");
    } catch (err) {
      setErro(err instanceof ErroApi ? err.message : "Não foi possível alterar a senha.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={enviar} className="max-w-sm space-y-3" noValidate>
      <div>
        <label htmlFor="senha-atual" className={rotulo}>
          Senha atual
        </label>
        <input id="senha-atual" type="password" autoComplete="current-password" value={atual} onChange={(e) => setAtual(e.target.value)} className={campo} required />
      </div>
      <div>
        <label htmlFor="senha-nova" className={rotulo}>
          Nova senha
        </label>
        <input
          id="senha-nova"
          type="password"
          autoComplete="new-password"
          value={nova}
          onChange={(e) => setNova(e.target.value)}
          className={campo}
          aria-describedby="senha-regra"
          required
        />
        <p id="senha-regra" className="mt-1 text-[11px] text-apagado">
          Mínimo de {MINIMO} caracteres. Ao trocar, as outras sessões são encerradas.
        </p>
      </div>
      <div>
        <label htmlFor="senha-confirmacao" className={rotulo}>
          Confirme a nova senha
        </label>
        <input
          id="senha-confirmacao"
          type="password"
          autoComplete="new-password"
          value={confirmacao}
          onChange={(e) => setConfirmacao(e.target.value)}
          className={campo}
          required
        />
      </div>
      {erro && (
        <p role="alert" className="text-sm text-baixa">
          {erro}
        </p>
      )}
      {sucesso && (
        <p role="status" className="text-sm text-alta">
          Senha alterada. As outras sessões foram encerradas.
        </p>
      )}
      <button type="submit" className={botao.primario} disabled={enviando}>
        {enviando ? "Salvando…" : "Alterar senha"}
      </button>
    </form>
  );
}
