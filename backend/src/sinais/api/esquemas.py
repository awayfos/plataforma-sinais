"""Esquemas do contrato da API v1 (``docs/api/contrato-v1.md``). Só Pydantic, sem FastAPI.

Instantes em ms UTC (``int``); preços de candle como string decimal; valores de análise como
``number`` (``null`` quando ainda não há histórico suficiente para calculá-los).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

type TempoTendencia = Literal["1m", "5m", "15m", "1h"]
type ExpiracaoRotulo = Literal["1m", "5m", "15m", "30m", "60m"]
type EventoEstrutura = Literal["BOS_ALTA", "BOS_BAIXA", "CHOCH_ALTA", "CHOCH_BAIXA"]
type TempoGraficoRotulo = Literal["1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"]


class _Saida(BaseModel):
    model_config = ConfigDict(frozen=True)


class _Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ------------------------------------------------------------------- erros
class CorpoErro(_Saida):
    codigo: str
    mensagem: str


class RespostaErro(_Saida):
    erro: CorpoErro


# ------------------------------------------------------- autenticação e conta
class AssinaturaUsuario(_Saida):
    plano: str | None
    status: Literal["ativa", "vencida", "bloqueada"]
    vence_em: int | None


class Usuario(_Saida):
    id: int
    email: str
    nome: str
    papel: Literal["cliente", "admin"]
    modo: Literal["essencial", "avancado"]
    assinatura: AssinaturaUsuario


class RespostaLogin(_Saida):
    usuario: Usuario


class LoginEntrada(_Entrada):
    email: str = Field(max_length=254)
    senha: str = Field(max_length=256)
    totp: str | None = Field(default=None, max_length=10)


class SenhaEntrada(_Entrada):
    senha_atual: str = Field(max_length=256)
    senha_nova: str = Field(min_length=10, max_length=256)


class PreferenciasEntrada(_Entrada):
    modo: Literal["essencial", "avancado"] | None = None
    layout: dict[str, Any] | None = None


# ------------------------------------------------------------------ mercado
class Ativo(_Saida):
    simbolo: str
    nome: str
    classe: str
    aberto: bool


class CandleSaida(_Saida):
    t: int
    o: str
    h: str
    l: str  # noqa: E741 - nome fixado pelo contrato
    c: str
    v: str


class CandleWs(CandleSaida):
    fechado: bool


class Regiao(_Saida):
    preco: float
    distancia_atr: float
    toques: int


class Regioes(_Saida):
    resistencia: Regiao | None
    suporte: Regiao | None


class Estrutura(_Saida):
    ultimo_evento: EventoEstrutura | None
    topo: float | None
    fundo: float | None


class VolumeAnalise(_Saida):
    relativo: float | None
    pressao_compradora: float | None


class Indicadores(_Saida):
    rsi: float | None
    macd_hist: float | None
    estoc_k: float | None
    bb_pct: float | None
    atr: float | None


class PriceAction(_Saida):
    impulso: float | None
    desaceleracao: float | None
    lateral: bool


class Analise(_Saida):
    simbolo: str
    t: int
    preco: str
    tendencia: dict[TempoTendencia, Literal[-1, 0, 1]]
    forca_tendencia: float | None
    regioes: Regioes
    estrutura: Estrutura
    volume: VolumeAnalise
    indicadores: Indicadores
    price_action: PriceAction
    resumo: list[str]


class Sinal(_Saida):
    expiracao: ExpiracaoRotulo
    direcao: Literal["COMPRA", "VENDA", "AGUARDAR"]
    probabilidade: float | None
    n_validacao: int | None
    motivo: str
    janela_ate: int | None
    invalidacao: str | None
    modelo: str | None


class SinalHistorico(_Saida):
    id: str
    simbolo: str
    expiracao: ExpiracaoRotulo
    direcao: Literal["COMPRA", "VENDA", "AGUARDAR"]
    gerado_em: int
    preco_referencia: str
    resultado: Literal["WIN", "LOSS", "TIE", "SEM_DADO"] | None
    apertado: bool | None


# -------------------------------------------------------------------- admin
class UsuarioAdmin(Usuario):
    status: Literal["ativo", "bloqueado", "desativado"]
    criado_em: int


class NovoUsuarioEntrada(_Entrada):
    email: str = Field(max_length=254)
    nome: str = Field(min_length=1, max_length=120)
    senha_temporaria: str = Field(min_length=10, max_length=256)
    plano: int | str
    vence_em: int | None = Field(default=None, ge=0)


class EdicaoUsuarioEntrada(_Entrada):
    nome: str | None = Field(default=None, min_length=1, max_length=120)
    email: str | None = Field(default=None, max_length=254)
    status: Literal["ativo", "bloqueado", "desativado"] | None = None
    senha_temporaria: str | None = Field(default=None, min_length=10, max_length=256)


class RecursosPlano(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ativos: list[str]
    expiracoes: list[ExpiracaoRotulo]
    modo_avancado: bool
    cursos: bool


class Plano(_Saida):
    id: int
    nome: str
    duracao_dias: int
    preco_centavos: int
    recursos: RecursosPlano
    ativo: bool


class PlanoEntrada(_Entrada):
    nome: str = Field(min_length=1, max_length=80)
    duracao_dias: int = Field(gt=0, le=3660)
    preco_centavos: int = Field(ge=0)
    recursos: RecursosPlano
    ativo: bool = True


class PlanoEdicao(_Entrada):
    nome: str | None = Field(default=None, min_length=1, max_length=80)
    duracao_dias: int | None = Field(default=None, gt=0, le=3660)
    preco_centavos: int | None = Field(default=None, ge=0)
    recursos: RecursosPlano | None = None
    ativo: bool | None = None


class AssinaturaEntrada(_Entrada):
    usuario_id: int
    plano_id: int
    inicio: int = Field(ge=0)
    fim: int = Field(ge=0)


class Assinatura(_Saida):
    id: int
    usuario_id: int
    plano_id: int
    inicio: int
    fim: int
    origem: str


class Acesso(_Saida):
    id: int
    usuario_id: int | None
    evento: str
    ip: str
    user_agent: str
    t: int


class RegistroAuditoria(_Saida):
    id: int
    admin_id: int
    acao: str
    alvo: str
    antes: dict[str, Any] | None
    depois: dict[str, Any] | None
    t: int


class Payout(BaseModel):
    model_config = ConfigDict(extra="forbid")

    simbolo: str
    expiracao: ExpiracaoRotulo
    payout: float = Field(gt=0, le=1)


class EventoQualidade(_Saida):
    simbolo: str
    intervalo: str
    inicio: int
    fim: int
    tipo: str


# ------------------------------------------------------------------ público
class EstatisticaPublica(_Saida):
    simbolo: str
    expiracao: ExpiracaoRotulo
    n: int
    taxa: float | None
    inicio: int | None
    fim: int | None
