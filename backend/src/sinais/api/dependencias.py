"""Dependências de autenticação e autorização (checadas no servidor em toda requisição)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from sinais.api.servicos import Servicos
from sinais.api.ws_canais import ip_do_cliente
from sinais.contas.contexto import Contexto

COOKIE_SESSAO = "sinais_sessao"
COOKIE_CSRF = "sinais_csrf"
COOKIE_DISPOSITIVO = "sinais_dispositivo"
CABECALHO_CSRF = "X-CSRF-Token"


def servicos(request: Request) -> Servicos:
    s: Servicos = request.app.state.servicos
    return s


Svc = Annotated[Servicos, Depends(servicos)]


def ip_cliente(request: Request, s: Servicos) -> str:
    conexao: str | None = request.client.host if request.client else None
    encaminhado: str | None = request.headers.get("x-forwarded-for")
    return ip_do_cliente(conexao, encaminhado, s.proxies_confiaveis)


async def sessao(request: Request, s: Svc) -> Contexto:
    return await s.contas.autenticar(request.cookies.get(COOKIE_SESSAO))


Sessao = Annotated[Contexto, Depends(sessao)]


async def assinante(ctx: Sessao, s: Svc) -> Contexto:
    s.contas.exigir_assinatura(ctx)
    return ctx


async def mutacao(request: Request, ctx: Sessao, s: Svc) -> Contexto:
    s.contas.verificar_csrf(
        ctx, request.headers.get(CABECALHO_CSRF), request.cookies.get(COOKIE_CSRF)
    )
    return ctx


async def admin(ctx: Sessao, s: Svc) -> Contexto:
    s.contas.exigir_admin(ctx)
    return ctx


async def admin_mutacao(ctx: Annotated[Contexto, Depends(mutacao)], s: Svc) -> Contexto:
    s.contas.exigir_admin(ctx)
    return ctx


Assinante = Annotated[Contexto, Depends(assinante)]
Mutacao = Annotated[Contexto, Depends(mutacao)]
Admin = Annotated[Contexto, Depends(admin)]
AdminMutacao = Annotated[Contexto, Depends(admin_mutacao)]
