"use client";

import { useRouter } from "next/navigation";
import { useRef, useState, type FormEvent } from "react";
import { ErroApi } from "@/lib/api/cliente";
import { api } from "@/lib/api/endpoints";
import { botao, campo, rotulo } from "@/components/ui/estilos";

/** Só caminhos internos (evita redirecionamento aberto). */
export function destinoSeguro(proximo: string | null | undefined): string {
  if (!proximo || !proximo.startsWith("/") || proximo.startsWith("//") || proximo.startsWith("/\\")) return "/terminal";
  if (proximo === "/login" || proximo.startsWith("/login?")) return "/terminal";
  return proximo;
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
            className={`${campo} num text-center text-lg tracking-[0.5em]`}
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
