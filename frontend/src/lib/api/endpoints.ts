import { requisicao } from "./cliente";
import type {
  Analise,
  Ativo,
  Candle,
  Desenho,
  EventoAcesso,
  EventoAuditoria,
  EventoQualidade,
  Id,
  LayoutUsuario,
  Modo,
  NovaAssinatura,
  NovoUsuario,
  PayoutExnova,
  Plano,
  Sinal,
  SinalHistorico,
  StatusUsuario,
  TempoGrafico,
  Usuario,
  UsuarioAdmin,
} from "./tipos";

type Parametro = string | number | null | undefined;

export function consulta(params: Record<string, Parametro>): string {
  const s = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") s.set(k, String(v));
  }
  const texto = s.toString();
  return texto ? `?${texto}` : "";
}

export const api = {
  login: (dados: { email: string; senha: string; totp?: string }) =>
    requisicao<{ usuario: Usuario }>("/api/auth/login", { metodo: "POST", corpo: dados, semRedirecionar: true }),
  logout: () => requisicao<void>("/api/auth/logout", { metodo: "POST", semRedirecionar: true }),
  eu: (opcoes: { semRedirecionar?: boolean; sinal?: AbortSignal } = {}) => requisicao<Usuario>("/api/eu", opcoes),
  trocarSenha: (dados: { senha_atual: string; senha_nova: string }) =>
    requisicao<void>("/api/eu/senha", { metodo: "POST", corpo: dados }),
  salvarPreferencias: (dados: { modo?: Modo; layout?: LayoutUsuario }) =>
    requisicao<Usuario>("/api/eu/preferencias", { metodo: "PATCH", corpo: dados }),

  ativos: (sinal?: AbortSignal) => requisicao<Ativo[]>("/api/ativos", { sinal }),
  candles: (p: { simbolo: string; tg: TempoGrafico; ate?: number; limite?: number }, sinal?: AbortSignal) =>
    requisicao<Candle[]>(`/api/candles${consulta(p)}`, { sinal }),
  analise: (simbolo: string, sinal?: AbortSignal) =>
    requisicao<Analise>(`/api/analise${consulta({ simbolo })}`, { sinal }),
  sinais: (simbolo: string, sinal?: AbortSignal) => requisicao<Sinal[]>(`/api/sinais${consulta({ simbolo })}`, { sinal }),
  historico: (p: { simbolo?: string; inicio?: number; fim?: number }, sinal?: AbortSignal) =>
    requisicao<SinalHistorico[]>(`/api/sinais/historico${consulta(p)}`, { sinal }),

  admin: {
    usuarios: (p: { busca?: string; status?: string }, sinal?: AbortSignal) =>
      requisicao<UsuarioAdmin[]>(`/api/admin/usuarios${consulta(p)}`, { sinal }),
    criarUsuario: (dados: NovoUsuario) =>
      requisicao<UsuarioAdmin>("/api/admin/usuarios", { metodo: "POST", corpo: dados }),
    editarUsuario: (id: Id, dados: Partial<{ email: string; nome: string; status: StatusUsuario }>) =>
      requisicao<UsuarioAdmin>(`/api/admin/usuarios/${encodeURIComponent(String(id))}`, { metodo: "PATCH", corpo: dados }),
    planos: (sinal?: AbortSignal) => requisicao<Plano[]>("/api/admin/planos", { sinal }),
    criarPlano: (dados: Omit<Plano, "id">) => requisicao<Plano>("/api/admin/planos", { metodo: "POST", corpo: dados }),
    editarPlano: (dados: Plano) => requisicao<Plano>("/api/admin/planos", { metodo: "PATCH", corpo: dados }),
    salvarAssinatura: (dados: NovaAssinatura) =>
      requisicao<unknown>("/api/admin/assinaturas", { metodo: "POST", corpo: dados }),
    acessos: (p: { usuario_id?: Id }, sinal?: AbortSignal) =>
      requisicao<EventoAcesso[]>(`/api/admin/acessos${consulta({ usuario_id: p.usuario_id })}`, { sinal }),
    auditoria: (sinal?: AbortSignal) => requisicao<EventoAuditoria[]>("/api/admin/auditoria", { sinal }),
    payout: (sinal?: AbortSignal) => requisicao<PayoutExnova[]>("/api/admin/corretoras/exnova/payout", { sinal }),
    salvarPayout: (lista: PayoutExnova[]) =>
      requisicao<PayoutExnova[]>("/api/admin/corretoras/exnova/payout", { metodo: "PUT", corpo: lista }),
    qualidade: (sinal?: AbortSignal) => requisicao<EventoQualidade[]>("/api/admin/qualidade", { sinal }),
  },
};

export type { Desenho };
