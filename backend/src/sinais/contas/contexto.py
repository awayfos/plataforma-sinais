"""Contexto de uma requisição autenticada: usuário, sessão, assinatura e plano."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sinais.contas.modelos import Assinatura, Papel, Plano, Sessao, StatusUsuario, Usuario
from sinais.core.tempo import InstanteMs

type StatusAssinatura = Literal["ativa", "vencida", "bloqueada"]


def status_assinatura(
    usuario: Usuario, assinatura: Assinatura | None, agora: InstanteMs
) -> StatusAssinatura:
    """``fim`` é exclusivo: no instante ``fim`` a assinatura já está vencida."""
    if usuario.status is not StatusUsuario.ATIVO:
        return "bloqueada"
    if assinatura is None or assinatura.fim <= agora:
        return "vencida"
    return "ativa"


@dataclass(frozen=True, slots=True)
class Contexto:
    usuario: Usuario
    sessao: Sessao
    assinatura: Assinatura | None
    plano: Plano | None
    agora: InstanteMs

    @property
    def admin(self) -> bool:
        return self.usuario.papel is Papel.ADMIN

    @property
    def status_assinatura(self) -> StatusAssinatura:
        return status_assinatura(self.usuario, self.assinatura, self.agora)
