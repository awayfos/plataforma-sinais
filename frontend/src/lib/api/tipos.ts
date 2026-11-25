// Tipos do contrato da API v1 (docs/api/contrato-v1.md).
// Campos marcados "fora do contrato v1" são opcionais: a tela só os usa se o backend enviar.

export type Id = number | string;
/** Instante em milissegundos UTC. */
export type Ms = number;
/** Preço como string decimal (precisão preservada). */
export type Decimal = string;

export type Papel = "cliente" | "admin";
export type Modo = "essencial" | "avancado";
export type StatusAssinatura = "ativa" | "vencida" | "bloqueada";

export interface Assinatura {
  plano: string;
  status: StatusAssinatura;
  vence_em: Ms | null;
}

export const TEMPOS_GRAFICOS = ["1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"] as const;
export type TempoGrafico = (typeof TEMPOS_GRAFICOS)[number];

export const EXPIRACOES = ["1m", "5m", "15m", "30m", "60m"] as const;
export type Expiracao = (typeof EXPIRACOES)[number];

export type Desenho =
  | { id: string; tipo: "linha"; preco: number }
  | { id: string; tipo: "zona"; de: number; ate: number };

export interface IndicadoresGrafico {
  ema: boolean;
  bollinger: boolean;
  vwap: boolean;
  rsi: boolean;
  macd: boolean;
}

/** Conteúdo livre de `layout` em PATCH /api/eu/preferencias (definido pelo frontend). */
export interface LayoutUsuario {
  desenhos?: Record<string, Desenho[]>;
  indicadores?: Partial<IndicadoresGrafico>;
  tempo?: TempoGrafico;
  simbolo?: string;
}

export interface Usuario {
  id: Id;
  email: string;
  nome: string;
  papel: Papel;
  modo: Modo;
  assinatura: Assinatura;
  /** Fora do contrato v1: o GET /api/eu ainda não devolve o layout salvo. */
  layout?: LayoutUsuario | null;
}

export interface Ativo {
  simbolo: string;
  nome: string;
  classe: string;
  aberto: boolean;
}

export interface Candle {
  t: Ms;
  o: Decimal;
  h: Decimal;
  l: Decimal;
  c: Decimal;
  v: Decimal | number;
}

export interface CandleAoVivo extends Candle {
  fechado: boolean;
}

export type TempoTendencia = "1m" | "5m" | "15m" | "1h";
export type Direcao3 = -1 | 0 | 1;

export interface Regiao {
  preco: number;
  distancia_atr: number;
  toques: number;
}

export type EventoEstrutura = "BOS_ALTA" | "BOS_BAIXA" | "CHOCH_ALTA" | "CHOCH_BAIXA";

export interface Analise {
  simbolo: string;
  t: Ms;
  preco: number | Decimal;
  tendencia: Record<TempoTendencia, Direcao3>;
  forca_tendencia: number;
  regioes: { resistencia: Regiao | null; suporte: Regiao | null };
  estrutura: { ultimo_evento: EventoEstrutura | null; topo: number | null; fundo: number | null };
  volume: { relativo: number; pressao_compradora: number };
  indicadores: { rsi: number; macd_hist: number; estoc_k: number; bb_pct: number; atr: number };
  price_action: { impulso: number | boolean; desaceleracao: number | boolean; lateral: boolean };
  resumo: string[];
}

export type Direcao = "COMPRA" | "VENDA" | "AGUARDAR";

export interface Sinal {
  expiracao: Expiracao;
  direcao: Direcao;
  probabilidade: number | null;
  n_validacao: number | null;
  motivo: string;
  janela_ate: Ms | null;
  invalidacao: string | null;
  modelo: string | null;
  /** Fora do contrato v1 (design §12.6): tolerância de preço da entrada. */
  tolerancia_preco?: Decimal | null;
  /** Fora do contrato v1: preço de referência no momento da decisão. */
  preco_referencia?: Decimal | null;
}

export type Resultado = "WIN" | "LOSS" | "TIE" | "SEM_DADO";

export interface SinalHistorico {
  id: Id;
  simbolo: string;
  expiracao: Expiracao;
  direcao: Direcao;
  gerado_em: Ms;
  preco_referencia: Decimal;
  resultado: Resultado | null;
  apertado: boolean | null;
}

export interface RecursosPlano {
  ativos: string[];
  expiracoes: string[];
  modo_avancado: boolean;
  cursos: boolean;
}

export interface Plano {
  id: Id;
  nome: string;
  duracao_dias: number;
  preco_centavos: number;
  recursos: RecursosPlano;
  ativo: boolean;
}

export type StatusUsuario = "ativo" | "bloqueado" | "desativado";

/** Item de GET /api/admin/usuarios. O contrato não fixa o formato; campos extras são opcionais. */
export interface UsuarioAdmin {
  id: Id;
  email: string;
  nome: string;
  papel?: Papel;
  status?: StatusUsuario;
  assinatura?: Assinatura | null;
  criado_em?: Ms;
}

export interface NovoUsuario {
  email: string;
  nome: string;
  senha_temporaria: string;
  plano: Id;
  vence_em: Ms;
}

export interface NovaAssinatura {
  usuario_id: Id;
  plano_id: Id;
  inicio: Ms;
  fim: Ms;
}

export interface PayoutExnova {
  simbolo: string;
  expiracao: Expiracao;
  /** Fração (0,86 = 86%). */
  payout: number;
}

/** Formatos dos logs não fixados no contrato v1: campos opcionais. */
export interface EventoAcesso {
  id?: Id;
  usuario_id?: Id;
  email?: string;
  ts: Ms;
  evento: string;
  ip?: string | null;
  user_agent?: string | null;
}

export interface EventoAuditoria {
  id?: Id;
  admin_id?: Id;
  admin_email?: string;
  acao: string;
  alvo?: string | null;
  antes?: unknown;
  depois?: unknown;
  ts: Ms;
}

export interface EventoQualidade {
  id?: Id;
  simbolo?: string;
  inicio?: Ms;
  fim?: Ms | null;
  tipo: string;
  detalhes?: unknown;
}

export interface CorpoErro {
  erro: { codigo: string; mensagem: string };
}
