import type { Analise, CandleAoVivo, Sinal, TempoGrafico } from "../api/tipos";

export type Canal = `candles:${string}:${TempoGrafico}` | `analise:${string}` | `sinais:${string}`;

export type DadosDoCanal<C extends Canal> = C extends `candles:${string}`
  ? CandleAoVivo
  : C extends `analise:${string}`
    ? Analise
    : Sinal[];

export type StatusConexao = "ocioso" | "conectando" | "conectado" | "reconectando" | "encerrado";

export interface SocketMinimo {
  readyState: number;
  send(dados: string): void;
  close(codigo?: number): void;
  onopen: (() => void) | null;
  onclose: ((ev: { code: number }) => void) | null;
  onmessage: ((ev: { data: unknown }) => void) | null;
  onerror: (() => void) | null;
}

export interface OpcoesTempoReal {
  url: string;
  criarSocket?: (url: string) => SocketMinimo;
  agendar?: (fn: () => void, ms: number) => unknown;
  cancelar?: (id: unknown) => void;
  aleatorio?: () => number;
  aoMudarStatus?: (s: StatusConexao) => void;
  aoSessaoRevogada?: () => void;
  aoAssinaturaVencida?: () => void;
}

export const ATRASO_MINIMO_MS = 500;
export const ATRASO_MAXIMO_MS = 30_000;
const ABERTO = 1;

/** Backoff exponencial com jitter ("equal jitter"): entre metade e o total do atraso-base. */
export function atrasoReconexao(tentativa: number, aleatorio: () => number = Math.random): number {
  const base = Math.min(ATRASO_MAXIMO_MS, ATRASO_MINIMO_MS * 2 ** tentativa);
  return Math.round(base / 2 + (aleatorio() * base) / 2);
}

type Ouvinte = (dados: unknown) => void;

/** Um WebSocket por aba, multiplexado por canal (contrato v1, "Tempo real"). */
export class ClienteTempoReal {
  private socket: SocketMinimo | null = null;
  private readonly ouvintes = new Map<string, Set<Ouvinte>>();
  private tentativa = 0;
  private timer: unknown = null;
  private encerrado = false;
  private _status: StatusConexao = "ocioso";

  constructor(private readonly opcoes: OpcoesTempoReal) {}

  get status(): StatusConexao {
    return this._status;
  }

  assinar<C extends Canal>(canal: C, ouvinte: (dados: DadosDoCanal<C>) => void): () => void {
    let conjunto = this.ouvintes.get(canal);
    const novo = !conjunto;
    if (!conjunto) {
      conjunto = new Set();
      this.ouvintes.set(canal, conjunto);
    }
    const fn = ouvinte as Ouvinte;
    conjunto.add(fn);
    if (!this.encerrado && !this.socket && this.timer === null) this.conectar();
    else if (novo) this.enviar({ acao: "assinar", canal });

    return () => {
      const atual = this.ouvintes.get(canal);
      if (!atual) return;
      atual.delete(fn);
      if (atual.size === 0) {
        this.ouvintes.delete(canal);
        this.enviar({ acao: "cancelar", canal });
      }
    };
  }

  fechar(): void {
    this.encerrado = true;
    if (this.timer !== null) (this.opcoes.cancelar ?? ((id) => clearTimeout(id as number)))(this.timer);
    this.timer = null;
    const s = this.socket;
    this.socket = null;
    s?.close(1000);
    this.mudarStatus("encerrado");
  }

  /** Reabre depois de fechar() (ex.: remontagem do React em modo estrito). */
  retomar(): void {
    if (!this.encerrado) return;
    this.encerrado = false;
    this.tentativa = 0;
    if (this.ouvintes.size > 0) this.conectar();
    else this.mudarStatus("ocioso");
  }

  private enviar(msg: { acao: "assinar" | "cancelar"; canal: string }): void {
    if (this.socket && this.socket.readyState === ABERTO) this.socket.send(JSON.stringify(msg));
  }

  private conectar(): void {
    this.mudarStatus(this.tentativa === 0 ? "conectando" : "reconectando");
    const criar = this.opcoes.criarSocket ?? ((url: string) => new WebSocket(url) as unknown as SocketMinimo);
    const s = criar(this.opcoes.url);
    this.socket = s;

    s.onopen = () => {
      if (this.socket !== s) return;
      this.tentativa = 0;
      this.mudarStatus("conectado");
      for (const canal of this.ouvintes.keys()) this.enviar({ acao: "assinar", canal });
    };
    s.onmessage = (ev) => {
      if (this.socket !== s) return;
      let msg: unknown;
      try {
        msg = JSON.parse(String(ev.data));
      } catch {
        return;
      }
      if (!msg || typeof msg !== "object" || typeof (msg as { canal?: unknown }).canal !== "string") return;
      const { canal, dados } = msg as { canal: string; dados: unknown };
      const conjunto = this.ouvintes.get(canal);
      if (conjunto) for (const fn of [...conjunto]) fn(dados);
    };
    s.onerror = () => {};
    s.onclose = (ev) => {
      if (this.socket !== s) return;
      this.socket = null;
      if (this.encerrado) return;
      if (ev.code === 4401) {
        this.encerrado = true;
        this.mudarStatus("encerrado");
        this.opcoes.aoSessaoRevogada?.();
      } else if (ev.code === 4402) {
        this.encerrado = true;
        this.mudarStatus("encerrado");
        this.opcoes.aoAssinaturaVencida?.();
      } else {
        this.agendarReconexao();
      }
    };
  }

  private agendarReconexao(): void {
    const atraso = atrasoReconexao(this.tentativa, this.opcoes.aleatorio);
    this.tentativa += 1;
    this.mudarStatus("reconectando");
    const agendar = this.opcoes.agendar ?? ((fn: () => void, ms: number) => setTimeout(fn, ms));
    this.timer = agendar(() => {
      this.timer = null;
      if (!this.encerrado) this.conectar();
    }, atraso);
  }

  private mudarStatus(s: StatusConexao): void {
    if (this._status === s) return;
    this._status = s;
    this.opcoes.aoMudarStatus?.(s);
  }
}

export function urlTempoReal(): string {
  const configurada = process.env.NEXT_PUBLIC_WS_URL;
  if (configurada) return configurada;
  const protocolo = window.location.protocol === "https:" ? "wss" : "ws";
  return `${protocolo}://${window.location.host}/api/ws`;
}
