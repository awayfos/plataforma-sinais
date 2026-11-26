// Último preço por ativo, alimentado pelos ticks do gráfico e pelo canal `preco:SIMB`.
// Os componentes leem com useSyncExternalStore: só o número na tela re-renderiza, não o terminal.

export interface PrecoVivo {
  preco: string;
  /** Comparado ao preço anterior: 1 subiu, -1 caiu, 0 primeiro valor. */
  direcao: -1 | 0 | 1;
  seq: number;
}

const precos = new Map<string, PrecoVivo>();
const ouvintes = new Set<() => void>();
let seq = 0;

export function publicarPreco(simbolo: string, preco: string | number): void {
  const texto = typeof preco === "number" ? String(preco) : preco;
  const valor = Number(texto);
  if (!Number.isFinite(valor)) return;
  const anterior = precos.get(simbolo);
  if (anterior && Number(anterior.preco) === valor) return;
  const direcao = !anterior ? 0 : valor > Number(anterior.preco) ? 1 : -1;
  seq += 1;
  precos.set(simbolo, { preco: texto, direcao, seq });
  for (const fn of [...ouvintes]) fn();
}

export function lerPreco(simbolo: string): PrecoVivo | undefined {
  return precos.get(simbolo);
}

export function assinarPrecos(fn: () => void): () => void {
  ouvintes.add(fn);
  return () => ouvintes.delete(fn);
}

/** Extrai o preço do canal `preco:SIMB` (número, string ou objeto com `preco`/`p`/`c`). */
export function precoDoCanal(dados: unknown): string | number | null {
  if (typeof dados === "number" || typeof dados === "string") return dados;
  if (dados && typeof dados === "object") {
    const o = dados as Record<string, unknown>;
    for (const k of ["preco", "p", "c"]) {
      const v = o[k];
      if (typeof v === "number" || typeof v === "string") return v;
    }
  }
  return null;
}

/** Só para testes. */
export function redefinirPrecos(): void {
  precos.clear();
  seq = 0;
}
