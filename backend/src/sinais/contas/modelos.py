"""Tipos de domínio das contas. Instantes em milissegundos UTC (ADR-13)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from sinais.core.tempo import InstanteMs


class Papel(StrEnum):
    CLIENTE = "cliente"
    ADMIN = "admin"


class StatusUsuario(StrEnum):
    ATIVO = "ativo"
    BLOQUEADO = "bloqueado"
    DESATIVADO = "desativado"


class Modo(StrEnum):
    ESSENCIAL = "essencial"
    AVANCADO = "avancado"


@dataclass(frozen=True, slots=True)
class NovoUsuario:
    email: str
    nome: str
    papel: Papel
    senha_hash: str
    criado_em: InstanteMs
    totp_cifrado: str | None = None


@dataclass(frozen=True, slots=True)
class Usuario:
    id: int
    email: str
    nome: str
    papel: Papel
    status: StatusUsuario
    senha_hash: str
    totp_cifrado: str | None
    totp_ultimo_passo: int | None
    modo: Modo
    layout: dict[str, Any]
    criado_em: InstanteMs


@dataclass(frozen=True, slots=True)
class Recursos:
    """Permissões por recurso que os planos combinam (design §18)."""

    ativos: tuple[str, ...]
    expiracoes: tuple[str, ...]
    modo_avancado: bool
    cursos: bool


@dataclass(frozen=True, slots=True)
class NovoPlano:
    nome: str
    duracao_dias: int
    preco_centavos: int
    recursos: Recursos
    ativo: bool


@dataclass(frozen=True, slots=True)
class Plano:
    id: int
    nome: str
    duracao_dias: int
    preco_centavos: int
    recursos: Recursos
    ativo: bool


@dataclass(frozen=True, slots=True)
class Assinatura:
    id: int
    usuario_id: int
    plano_id: int
    inicio: InstanteMs
    fim: InstanteMs
    origem: str
    criado_em: InstanteMs


@dataclass(frozen=True, slots=True)
class Sessao:
    """Sessão no servidor. Só o hash do token (e do CSRF) é guardado."""

    token_hash: str
    csrf_hash: str
    usuario_id: int
    criada_em: InstanteMs
    ultimo_uso: InstanteMs
    expira_em: InstanteMs
    ip: str
    user_agent: str
    revogada_em: InstanteMs | None = None
    motivo_revogacao: str | None = None


@dataclass(frozen=True, slots=True)
class RegistroAcesso:
    id: int
    usuario_id: int | None
    evento: str
    ip: str
    user_agent: str
    t: InstanteMs


@dataclass(frozen=True, slots=True)
class RegistroAuditoria:
    id: int
    admin_id: int
    acao: str
    alvo: str
    antes: dict[str, Any] | None
    depois: dict[str, Any] | None
    t: InstanteMs


@dataclass(frozen=True, slots=True)
class ItemPayout:
    simbolo: str
    expiracao: str
    payout: float
