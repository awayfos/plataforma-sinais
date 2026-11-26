"""Autorização por recurso do plano (design §18). Admin vê tudo."""

from __future__ import annotations

from collections.abc import Sequence

from sinais.contas.contexto import Contexto


def pode_ver_ativo(ctx: Contexto, simbolo: str) -> bool:
    if ctx.admin:
        return True
    return ctx.plano is not None and simbolo in ctx.plano.recursos.ativos


def ativos_permitidos(ctx: Contexto, todos: Sequence[str]) -> tuple[str, ...]:
    return tuple(s for s in todos if pode_ver_ativo(ctx, s))


def expiracoes_permitidas(ctx: Contexto, todas: Sequence[str]) -> tuple[str, ...]:
    if ctx.admin:
        return tuple(todas)
    if ctx.plano is None:
        return ()
    return tuple(e for e in todas if e in ctx.plano.recursos.expiracoes)


def pode_modo_avancado(ctx: Contexto) -> bool:
    return ctx.admin or (ctx.plano is not None and ctx.plano.recursos.modo_avancado)
