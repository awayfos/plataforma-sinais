export function Marca({ compacta = false }: { compacta?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2">
      <svg viewBox="0 0 32 32" aria-hidden="true" className="size-6">
        <rect width="32" height="32" rx="7" fill="#131922" />
        <path d="M7 21l5-6 4 3 7-9" fill="none" stroke="#d6ad5c" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      {!compacta && (
        <span className="text-sm font-semibold tracking-tight text-texto">
          Plataforma <span className="text-ouro">Sinais</span>
        </span>
      )}
    </span>
  );
}
