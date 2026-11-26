import type { Metadata } from "next";
import { FormLogin } from "@/components/auth/FormLogin";
import { Marca } from "@/components/ui/Marca";

export const metadata: Metadata = { title: "Entrar" };

export default async function PaginaLogin({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const proximo = typeof params.proximo === "string" ? params.proximo : null;

  return (
    <main className="grid min-h-dvh lg:grid-cols-[1.1fr_1fr]">
      <section className="relative hidden overflow-hidden border-r border-borda bg-painel lg:flex lg:flex-col lg:justify-between lg:p-12">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 opacity-[0.35]"
          style={{
            backgroundImage:
              "linear-gradient(var(--color-borda) 1px, transparent 1px), linear-gradient(90deg, var(--color-borda) 1px, transparent 1px)",
            backgroundSize: "48px 48px",
            maskImage: "radial-gradient(ellipse at 30% 40%, black 20%, transparent 75%)",
          }}
        />
        <Marca />
        <div className="relative max-w-lg">
          <p className="mb-4 text-[11px] font-semibold tracking-[0.2em] text-ouro uppercase">Inteligência de mercado</p>
          <h1 className="text-4xl leading-tight font-semibold tracking-tight text-texto">
            Leia o mercado com clareza.
            <br />
            <span className="text-suave">Opere só quando houver vantagem.</span>
          </h1>
          <ul className="mt-8 space-y-3 text-sm text-suave">
            <li className="flex gap-3">
              <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-ouro" />
              Tendência, regiões difíceis de romper, estrutura e volume em tempo real.
            </li>
            <li className="flex gap-3">
              <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-ouro" />
              Sinais por expiração só onde a validação fora da amostra aprovou. Fora disso, AGUARDAR.
            </li>
            <li className="flex gap-3">
              <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-ouro" />
              Histórico completo e liquidação automática, incluindo as derrotas.
            </li>
          </ul>
        </div>
        <p className="relative text-xs text-apagado">
          Opções binárias têm alto risco. Nada aqui é promessa de retorno.
        </p>
      </section>

      <section className="flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm">
          <div className="mb-8 lg:hidden">
            <Marca />
          </div>
          <h2 className="text-xl font-semibold tracking-tight">Entrar</h2>
          <p className="mt-1 mb-8 text-sm text-apagado">Acesse com o e-mail da sua assinatura.</p>
          <FormLogin proximo={proximo} />
        </div>
      </section>
    </main>
  );
}
