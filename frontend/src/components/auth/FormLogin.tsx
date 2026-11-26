"use client";

import { useRouter } from "next/navigation";
import { useRef, useState, type FormEvent } from "react";
import { ErroApi } from "@/lib/api/cliente";
import { api } from "@/lib/api/endpoints";
import { botao, campo, campoBase, rotulo } from "@/components/ui/estilos";

const PADRAO = "/terminal";
const ORIGEM_REFERENCIA = "https://interno.invalid";

/**
 * Só caminhos internos (evita redirecionamento aberto). O navegador remove tabulação e quebras de linha
 * e trata "\\" como "/", então "/\t/evil.com" viraria "//evil.com": esses caracteres são recusados e o
 * resultado é conferido com o parser de URL (mesma origem).
 */
export function destinoSeguro(proximo: string | null | undefined): string {
  if (!proximo || !proximo.startsWith("/")) return PADRAO;
  if (/[\u0000-\u001f\u007f\\]/.test(proximo)) return PADRAO;
  let url: URL;
  try {
    url = new URL(proximo, ORIGEM_REFERENCIA);
  } catch {
    return PADRAO;
  }
  if (url.origin !== ORIGEM_REFERENCIA) return PADRAO;
  if (url.pathname === "/login") return PADRAO;
  return `${url.pathname}${url.search}${url.hash}`;
}

export function FormLogin({ proximo }: { proximo?: string | null }) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [totp, setTotp] = useState("");
  const [etapa, setEtapa] = useState<"credenciais" | "totp">("credenciais");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const campoTotp = useRef<HTMLInputElement>(null);

  async function enviar(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      await api.login({ email: email.trim(), senha, ...(etapa === "totp" ? { totp: totp.trim() } : {}) });
      router.replace(destinoSeguro(proximo));
    } catch (err) {
      if (err instanceof ErroApi && err.codigo === "totp_necessario" && etapa === "credenciais") {
        setEtapa("totp");
        setTimeout(() => campoTotp.current?.focus(), 0);
      } else {
        setErro(err instanceof ErroApi ? err.message : "Não foi possível entrar. Tente de novo.");
      }
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={enviar} className="space-y-4" noValidate aria-describedby={erro ? "erro-login" : undefined}>
      {etapa === "credenciais" ? (
        <>
          <div>
            <label htmlFor="email" className={rotulo}>
              E-mail
            </label>
            <input
              id="email"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={campo}
            />
          </div>
          <div>
            <label htmlFor="senha" className={rotulo}>
              Senha
            </label>
            <input
              id="senha"
              type="password"
              autoComplete="current-password"
              required
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              className={campo}
            />
          </div>
        </>
      ) : (
        <div>
          <p className="mb-3 text-sm text-suave">
            Conta de administrador. Digite o código de 6 dígitos do seu aplicativo autenticador.
          </p>
          <label htmlFor="totp" className={rotulo}>
            Código de verificação
          </label>
          <input
            id="totp"
            ref={campoTotp}
            inputMode="numeric"
            autoComplete="one-time-code"
            pattern="[0-9]{6}"
            maxLength={6}
            required
            value={totp}
            onChange={(e) => setTotp(e.target.value.replace(/\D/g, ""))}
            className={`${campoBase} num text-center text-lg tracking-[0.5em] py-2 w-full`}
          />
        </div>
      )}

      {erro && (
        <p id="erro-login" role="alert" className="rounded-md border border-baixa/30 bg-baixa/5 px-3 py-2 text-sm text-baixa">
          {erro}
        </p>
      )}

      <button type="submit" disabled={enviando} className={`${botao.primario} w-full`}>
        {enviando ? "Entrando…" : etapa === "credenciais" ? "Entrar" : "Verificar"}
      </button>

      {etapa === "totp" && (
        <button
          type="button"
          onClick={() => {
            setEtapa("credenciais");
            setTotp("");
            setErro(null);
          }}
          className={`${botao.fantasma} w-full`}
        >
          Voltar
        </button>
      )}
    </form>
  );
}
