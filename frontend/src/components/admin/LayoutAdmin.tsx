"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSessao } from "@/components/sessao/ProvedorSessao";
import { Carregando } from "@/components/ui/Estado";

const SECOES = [
  { href: "/admin/usuarios", rotulo: "Usuários" },
  { href: "/admin/planos", rotulo: "Planos" },
  { href: "/admin/assinaturas", rotulo: "Assinaturas" },
  { href: "/admin/acessos", rotulo: "Acessos" },
  { href: "/admin/auditoria", rotulo: "Auditoria" },
  { href: "/admin/payout", rotulo: "Payout Exnova" },
  { href: "/admin/qualidade", rotulo: "Qualidade de dados" },
];

export function LayoutAdmin({ children }: { children: React.ReactNode }) {
  const { usuario, carregando } = useSessao();
  const caminho = usePathname();

  if (carregando) return <main className="p-6"><Carregando /></main>;
  if (usuario?.papel !== "admin") {
    return (
      <main className="mx-auto max-w-md p-10 text-center">
        <h1 className="text-lg font-semibold">Acesso restrito</h1>
        <p className="mt-2 text-sm text-apagado">Esta área é só para administradores.</p>
      </main>
    );
  }

  const atual = SECOES.find((s) => caminho.startsWith(s.href));
  return (
    <div className="mx-auto grid w-full max-w-7xl gap-6 px-4 py-6 md:grid-cols-[200px_1fr]">
      <nav aria-label="Administração" className="md:sticky md:top-4 md:self-start">
        <p className="mb-2 px-2 text-[11px] font-semibold tracking-[0.12em] text-ouro uppercase">Administração</p>
        <ul className="flex gap-1 overflow-x-auto md:flex-col">
          {SECOES.map((s) => (
            <li key={s.href}>
              <Link
                href={s.href}
                aria-current={atual?.href === s.href ? "page" : undefined}
                className={`block rounded px-2.5 py-1.5 text-[13px] whitespace-nowrap transition-colors ${
                  atual?.href === s.href ? "bg-painel-2 text-texto" : "text-apagado hover:text-suave"
                }`}
              >
                {s.rotulo}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
      <main className="min-w-0">
        <h1 className="mb-4 text-lg font-semibold tracking-tight">{atual?.rotulo ?? "Administração"}</h1>
        {children}
      </main>
    </div>
  );
}
