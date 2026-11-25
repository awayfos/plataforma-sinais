// Classes compartilhadas (Tailwind) para botões, campos e tabelas.

export const botao = {
  primario:
    "inline-flex items-center justify-center gap-2 rounded-md bg-ouro px-4 py-2 text-sm font-semibold text-fundo transition hover:bg-ouro-claro disabled:cursor-not-allowed disabled:opacity-50",
  secundario:
    "inline-flex items-center justify-center gap-2 rounded-md border border-borda-forte bg-painel-2 px-3 py-1.5 text-sm font-medium text-texto transition hover:border-suave disabled:cursor-not-allowed disabled:opacity-50",
  fantasma:
    "inline-flex items-center justify-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium text-suave transition hover:bg-painel-2 hover:text-texto disabled:opacity-40",
  perigo:
    "inline-flex items-center justify-center gap-2 rounded-md border border-baixa/40 bg-baixa/10 px-3 py-1.5 text-xs font-semibold text-baixa transition hover:bg-baixa/20",
} as const;

export const campo =
  "w-full rounded-md border border-borda-forte bg-fundo px-3 py-2 text-sm text-texto placeholder:text-apagado transition focus:border-ouro focus:outline-none focus:ring-1 focus:ring-ouro/40";

export const rotulo = "mb-1 block text-xs font-medium text-suave";

export const painel = "rounded-lg border border-borda bg-painel";

export const tituloPainel = "text-[11px] font-semibold tracking-[0.12em] text-apagado uppercase";

export const tabela = {
  raiz: "w-full border-collapse text-left text-sm",
  cabeca: "border-b border-borda text-[11px] font-semibold tracking-wider text-apagado uppercase",
  th: "px-3 py-2 font-semibold",
  linha: "border-b border-borda/60 transition-colors hover:bg-painel-2/60",
  td: "px-3 py-2 align-top",
} as const;
