"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useStatusTempoReal } from "@/lib/ws/ProvedorTempoReal";
import { Marca } from "@/components/ui/Marca";
import { AlternadorModo } from "./AlternadorModo";
import { useSessao } from "./ProvedorSessao";

const ROTAS = [
  { href: "/terminal", rotulo: "Terminal" },
  { href: "/historico", rotulo: "Histórico" },
  { href: "/perfil", rotulo: "Perfil" },
];

const STATUS: Record<string, { texto: string; cor: string }> = {
  conectado: { texto: "Ao vivo", cor: "bg-alta" },
  conectando: { texto: "Conectando…", cor: "bg-alerta animate-pulse" },
  reconectando: { texto: "Reconectando…", cor: "bg-alerta animate-pulse" },
  encerrado: { texto: "Desconectado", cor: "bg-baixa" },
  indisponivel: { texto: "Ao vivo indisponível", cor: "bg-baixa" },
  ocioso: { texto: "Em espera", cor: "bg-apagado" },
};

export function Cabecalho() {
  const caminho = usePathname();
  const { usuario, sair } = useSessao();
  const estado = useStatusTempoReal();
  const status = STATUS[estado]!;
  const rotas = usuario?.papel === "admin" ? [...ROTAS, { href: "/admin/usuarios", rotulo: "Admin" }] : ROTAS;

  return (
    <header className="flex h-12 shrink-0 items-center gap-4 border-b border-borda bg-painel px-3 sm:px-4">
      <Link href="/terminal" aria-label="Plataforma Sinais — Terminal" className="shrink-0">
        <span className="hidden sm:inline">
          <Marca />
        </span>
        <span className="sm:hidden">
          <Marca compacta />
        </span>
      </Link>
      <nav aria-label="Principal" className="flex items-center gap-0.5 overflow-x-auto">
        {rotas.map((r) => {
          const ativa = caminho === r.href || caminho.startsWith(r.href.replace(/\/usuarios$/, ""));
          return (
            <Link
              key={r.href}
              href={r.href}
              aria-current={ativa ? "page" : undefined}
              className={`rounded px-2.5 py-1 text-[13px] font-medium whitespace-nowrap transition-colors ${
                ativa ? "bg-painel-2 text-texto" : "text-apagado hover:text-suave"
              }`}
            >
              {r.rotulo}
            </Link>
          );
        })}
      </nav>
      <div className="ml-auto flex items-center gap-3">
        {estado !== "ocioso" && (
          <span className="inline-flex items-center gap-1.5 text-[11px] text-apagado" role="status" aria-live="polite" title={status.texto}>
            <span className={`size-2 rounded-full ${status.cor}`} aria-hidden="true" />
            <span className="sr-only md:not-sr-only">{status.texto}</span>
          </span>
        )}
        <div className="hidden sm:block">
          <AlternadorModo />
        </div>
        <button
          type="button"
          onClick={() => void sair()}
          className="rounded px-2 py-1 text-xs font-medium text-apagado transition-colors hover:text-texto"
        >
          Sair
        </button>
      </div>
    </header>
  );
}
