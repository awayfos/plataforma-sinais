"""Fábrica do app FastAPI (contrato v1)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request, Response

from sinais.api import erros
from sinais.api.rotas import admin, auth, eu, mercado, publico
from sinais.api.servicos import Servicos
from sinais.api.ws import rota_ws
from sinais.logs import obter_logger

_log = obter_logger(__name__)
VERSAO_API = "1.0.0"


def criar_app(servicos: Servicos) -> FastAPI:
    @asynccontextmanager
    async def ciclo(_: FastAPI) -> AsyncIterator[None]:
        tarefa: asyncio.Task[None] | None = None
        if servicos.fonte_eventos is not None:
            tarefa = asyncio.create_task(servicos.fonte_eventos(servicos))
        yield
        if tarefa is not None:
            tarefa.cancel()
            with suppress(asyncio.CancelledError, Exception):
                await tarefa

    app = FastAPI(
        title="Plataforma Sinais — API",
        version=VERSAO_API,
        lifespan=ciclo,
        openapi_url="/api/openapi.json" if servicos.documentacao else None,
        docs_url="/api/docs" if servicos.documentacao else None,
        redoc_url=None,
    )
    app.state.servicos = servicos
    erros.instalar(app)

    @app.middleware("http")
    async def cabecalhos(
        request: Request, seguinte: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        resposta = await seguinte(request)
        h = resposta.headers
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("X-Frame-Options", "DENY")
        h.setdefault("Referrer-Policy", "no-referrer")
        h.setdefault("Cache-Control", "no-store")
        if not request.url.path.startswith("/api/docs"):
            h.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        if servicos.cookie_seguro:
            h.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return resposta

    for modulo in (auth, eu, mercado, admin, publico):
        app.include_router(modulo.rotas)
    app.add_api_websocket_route("/api/ws", rota_ws)
    return app
