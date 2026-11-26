import type { Analise, CandleAoVivo, ErroCanal, Sinal, TempoGrafico } from "../api/tipos";

export type Canal = `candles:${string}:${TempoGrafico}` | `analise:${string}` | `sinais:${string}`;

export type DadosDoCanal<C extends Canal> = C extends `candles:${string}`
  ? CandleAoVivo
  : C extends `analise:${string}`
    ? Analise
    : Sinal[];

/** "indisponivel": o servidor recusa o handshake mas a sessão HTTP está válida; tenta de novo devagar. */
export type StatusConexao = "ocioso" | "conectando" | "conectado" | "reconectando" | "indisponivel" | "encerrado";

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
  /** Conexão reaberta depois de uma queda: hora de recarregar o que veio por REST. */
  aoReconectar?: () => void;
  /**
   * A cada FALHAS_PARA_CONFERIR quedas seguidas sem uma conexão estável. Um handshake recusado (sessão ou
   * assinatura inválida) chega ao navegador só como 1006; o chamador confere a sessão por HTTP.
   */
  aoFalhasSeguidas?: () => void;
}

export const FALHAS_PARA_CONFERIR = 3;
export const ATRASO_LENTO_MS = 60_000;

export const ATRASO_MINIMO_MS = 500;
export const ATRASO_MAXIMO_MS = 30_000;
const ABERTO = 1;

/** Backoff exponencial com jitter ("equal jitter"): entre metade e o total do atraso-base. */
export function atrasoReconexao(tentativa: number, aleatorio: () => number = Math.random): number {
  const base = Math.min(ATRASO_MAXIMO_MS, ATRASO_MINIMO_MS * 2 ** tentativa);
  return Math.round(base / 2 + (aleatorio() * base) / 2);
}

type Ouvinte = (dados: unknown) => void;
type OuvinteErro = (erro: ErroCanal) => void;

/** Um WebSocket por aba, multiplexado por canal (contrato v1, "Tempo real"). */
export class ClienteTempoReal {
  private socket: SocketMinimo | null = null;
  private readonly ouvintes = new Map<string, Set<Ouvinte>>();
  private readonly ouvintesErro = new Map<string, Set<OuvinteErro>>();
  private lento = false;
  private tentativa = 0;
  private timer: unknown = null;
  private encerrado = false;
  private jaAbriu = false;
  private _status: StatusConexao = "ocioso";

  constructor(private readonly opcoes: OpcoesTempoReal) {}

  get status(): StatusConexao {
    return this._status;
  }

  assinar<C extends Canal>(
    canal: C,
    ouvinte: (dados: DadosDoCanal<C>) => void,
    aoErro?: (erro: ErroCanal) => void,
  ): () => void {
    let conjunto = this.ouvintes.get(canal);
    const novo = !conjunto;
    if (!conjunto) {
      conjunto = new Set();
      this.ouvintes.set(canal, conjunto);
    }
    const fn = ouvinte as Ouvinte;
    conjunto.add(fn);
    if (aoErro) {
      const erros = this.ouvintesErro.get(canal) ?? new Set<OuvinteErro>();
      erros.add(aoErro);
      this.ouvintesErro.set(canal, erros);
    }
    if (!this.encerrado && !this.socket && this.timer === null) this.conectar();
    else if (novo) this.enviar({ acao: "assinar", canal });

    return () => {
      const atual = this.ouvintes.get(canal);
      if (!atual) return;
      atual.delete(fn);
      if (aoErro) this.ouvintesErro.get(canal)?.delete(aoErro);
      if (atual.size === 0) {
        this.ouvintesErro.delete(canal);
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

  /**
   * Handshake recusado com a sessão HTTP válida (ex.: 4403 de Origem, que o navegador vê como 1006):
   * para o laço rápido e tenta de novo a cada minuto, com status "indisponivel", até conectar.
   */
  desacelerar(): void {
    if (this.encerrado || this.lento) return;
    this.lento = true;
    this.mudarStatus("indisponivel");
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
    this.mudarStatus(this.lento ? "indisponivel" : this.tentativa === 0 ? "conectando" : "reconectando");
    const criar = this.opcoes.criarSocket ?? ((url: string) => new WebSocket(url) as unknown as SocketMinimo);
    const s = criar(this.opcoes.url);
    this.socket = s;

    s.onopen = () => {
      if (this.socket !== s) return;
      this.tentativa = 0;
      this.lento = false;
      this.mudarStatus("conectado");
      for (const canal of this.ouvintes.keys()) this.enviar({ acao: "assinar", canal });
      if (this.jaAbriu) this.opcoes.aoReconectar?.();
      this.jaAbriu = true;
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
      const { canal, dados, erro } = msg as { canal: string; dados?: unknown; erro?: ErroCanal };
      // Quadro de erro ({canal, erro}, sem dados): nunca entregue como dados.
      if (erro !== undefined || dados === undefined) {
        if (erro) for (const fn of [...(this.ouvintesErro.get(canal) ?? [])]) fn(erro);
        return;
      }
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
    const atraso = this.lento ? ATRASO_LENTO_MS : atrasoReconexao(this.tentativa, this.opcoes.aleatorio);
    this.tentativa += 1;
    this.mudarStatus(this.lento ? "indisponivel" : "reconectando");
    if (!this.lento && this.tentativa % FALHAS_PARA_CONFERIR === 0) this.opcoes.aoFalhasSeguidas?.();
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
