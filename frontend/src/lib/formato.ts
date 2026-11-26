// Formatação pt-BR. Horários sempre em Brasília (dados trafegam em ms UTC).

export const FUSO = "America/Sao_Paulo";

function agrupar(inteiro: string): string {
  return inteiro.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

/**
 * Preço da API (string decimal) sem passar por float: remove zeros à direita,
 * mantém ao menos 2 casas, separador de milhar "." e decimal ",".
 */
export function formatarPreco(valor: string | number | null | undefined): string {
  if (valor === null || valor === undefined || valor === "") return "—";
  const texto = typeof valor === "number" ? numeroParaTexto(valor) : valor.trim();
  const m = /^(-?)(\d+)(?:\.(\d+))?$/.exec(texto);
  if (!m) return texto;
  const [, sinal, inteiro, fracao = ""] = m;
  let casas = fracao.replace(/0+$/, "");
  if (casas.length < 2) casas = casas.padEnd(2, "0");
  return `${sinal}${agrupar(inteiro!.replace(/^0+(?=\d)/, ""))},${casas}`;
}

function numeroParaTexto(n: number): string {
  if (!Number.isFinite(n)) return String(n);
  return n.toFixed(8);
}

export function formatarNumero(n: number | null | undefined, casas = 1): string {
  if (n === null || n === undefined || !Number.isFinite(n)) return "—";
  return new Intl.NumberFormat("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas }).format(n);
}

export function formatarPercentual(fracao: number | null | undefined, casas = 1): string {
  if (fracao === null || fracao === undefined || !Number.isFinite(fracao)) return "—";
  return `${formatarNumero(fracao * 100, casas)}%`;
}

export function formatarMoeda(centavos: number): string {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(centavos / 100);
}

const fmtHora = new Intl.DateTimeFormat("pt-BR", {
  timeZone: FUSO,
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hourCycle: "h23",
});
const fmtDataHora = new Intl.DateTimeFormat("pt-BR", {
  timeZone: FUSO,
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});
const fmtData = new Intl.DateTimeFormat("pt-BR", { timeZone: FUSO, day: "2-digit", month: "2-digit", year: "numeric" });

export function formatarHora(ms: number): string {
  return fmtHora.format(ms);
}

export function formatarDataHora(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return "—";
  return fmtDataHora.format(ms);
}

export function formatarData(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return "—";
  return fmtData.format(ms);
}

/** Contagem regressiva: arredonda para cima ("0:24" enquanto restar algo de 24 s). */
export function formatarDuracao(ms: number): string {
  const total = Math.max(0, Math.ceil(ms / 1000));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const ss = String(s).padStart(2, "0");
  return h > 0 ? `${h}:${String(m).padStart(2, "0")}:${ss}` : `${m}:${ss}`;
}

export function diasAte(ms: number, agora = Date.now()): number {
  return Math.ceil((ms - agora) / 86_400_000);
}

/** Intervalo [agora − dias, agora] em ms. Fora dos componentes: Date.now é impuro. */
export function periodoAteAgora(dias: number): { inicio: number; fim: number } {
  const fim = Date.now();
  return { inicio: fim - dias * 86_400_000, fim };
}

/** Tempo até o fechamento do candle, como no rótulo do eixo da Binance: "00:37", "03:01:01", "2d 01:00". */
export function formatarContagemVela(ms: number): string {
  const total = Math.max(0, Math.ceil(ms / 1000));
  const d = Math.floor(total / 86_400);
  const h = Math.floor((total % 86_400) / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const p = (n: number) => String(n).padStart(2, "0");
  if (d > 0) return `${d}d ${p(h)}:${p(m)}`;
  if (h > 0) return `${p(h)}:${p(m)}:${p(s)}`;
  return `${p(m)}:${p(s)}`;
}
