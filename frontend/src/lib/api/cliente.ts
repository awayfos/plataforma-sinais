import type { CorpoErro } from "./tipos";

export class ErroApi extends Error {
  readonly status: number;
  readonly codigo: string;

  constructor(status: number, codigo: string, mensagem: string) {
    super(mensagem);
    this.name = "ErroApi";
    this.status = status;
    this.codigo = codigo;
  }
}

export interface TratadorSessao {
  aoNaoAutenticado(): void;
  aoAssinaturaVencida(): void;
}

let tratador: TratadorSessao = { aoNaoAutenticado() {}, aoAssinaturaVencida() {} };

/** Registrado pelo provedor de sessão: o que fazer com 401 e 402 em qualquer chamada. */
export function definirTratadorSessao(t: TratadorSessao): void {
  tratador = t;
}

export function lerCookie(nome: string): string | null {
  if (typeof document === "undefined") return null;
  for (const parte of document.cookie.split(";")) {
    const [chave, ...resto] = parte.trim().split("=");
    if (chave === nome) return decodeURIComponent(resto.join("="));
  }
  return null;
}

export const MENSAGEM_LIMITE = "Muitas requisições. Aguarde alguns segundos e tente de novo.";

export interface OpcoesRequisicao {
  metodo?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  corpo?: unknown;
  sinal?: AbortSignal;
  /** Não redireciona em 401/402 (login, logout, tela de assinatura). */
  semRedirecionar?: boolean;
}

export async function requisicao<T>(caminho: string, opcoes: OpcoesRequisicao = {}): Promise<T> {
  const metodo = opcoes.metodo ?? "GET";
  const headers: Record<string, string> = { Accept: "application/json" };
  if (opcoes.corpo !== undefined) headers["Content-Type"] = "application/json";
  if (metodo !== "GET") {
    const csrf = lerCookie("sinais_csrf");
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }

  let resposta: Response;
  try {
    resposta = await fetch(caminho, {
      method: metodo,
      headers,
      body: opcoes.corpo === undefined ? undefined : JSON.stringify(opcoes.corpo),
      credentials: "same-origin",
      cache: "no-store",
      signal: opcoes.sinal,
    });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    throw new ErroApi(0, "rede", "Sem conexão com o servidor. Verifique sua internet e tente de novo.");
  }

  if (resposta.ok) {
    if (resposta.status === 204) return undefined as T;
    const texto = await resposta.text();
    return (texto ? JSON.parse(texto) : undefined) as T;
  }

  const erro = await lerErro(resposta);
  if (!opcoes.semRedirecionar) {
    if (erro.status === 401) tratador.aoNaoAutenticado();
    if (erro.status === 402) tratador.aoAssinaturaVencida();
  }
  throw erro;
}

async function lerErro(resposta: Response): Promise<ErroApi> {
  if (resposta.status === 429) return new ErroApi(429, "limite", MENSAGEM_LIMITE);
  try {
    const corpo = (await resposta.json()) as Partial<CorpoErro> | null;
    if (corpo?.erro?.mensagem) {
      return new ErroApi(resposta.status, corpo.erro.codigo ?? "erro", corpo.erro.mensagem);
    }
  } catch {
    // corpo não JSON (proxy, HTML): cai na mensagem genérica
  }
  return new ErroApi(
    resposta.status,
    "inesperado",
    `Erro inesperado (${resposta.status}). Tente de novo em instantes.`,
  );
}

export function paraErroApi(e: unknown): ErroApi {
  if (e instanceof ErroApi) return e;
  return new ErroApi(0, "inesperado", "Algo deu errado. Tente de novo.");
}
