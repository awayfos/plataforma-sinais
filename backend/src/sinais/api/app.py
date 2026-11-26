"""Fábrica do app FastAPI (contrato v1)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request, Response

from sinais.api import erros
from sinais.api.rotas import admin, auth, eu, mercado, publico
from sinais.api.servicos import Servicos
from sinais.api.supervisao import supervisionar
from sinais.api.ws import rota_ws
from sinais.logs import obter_logger

_log = obter_logger(__name__)
VERSAO_API = "1.0.0"


def criar_app(servicos: Servicos) -> FastAPI:
    @asynccontextmanager
    async def ciclo(_: FastAPI) -> AsyncIterator[None]:
        tarefas: list[asyncio.Task[None]] = []
        fonte = servicos.fonte_eventos
        if fonte is not None:
            tarefas.append(
                asyncio.create_task(supervisionar("fonte_eventos", lambda: fonte(servicos)))
            )
        for nome, fabrica in servicos.tarefas:
            tarefas.append(asyncio.create_task(supervisionar(nome, fabrica)))
        yield
        for tarefa in tarefas:
            tarefa.cancel()
        for tarefa in tarefas:
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
    erros.instalar(app, servicos.cookie_seguro)

    @app.middleware("http")
    async def cabecalhos(
        request: Request, seguinte: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        resposta = await seguinte(request)
        docs = request.url.path.startswith("/api/docs")
        for nome, valor in erros.cabecalhos_seguranca(servicos.cookie_seguro, docs).items():
            resposta.headers.setdefault(nome, valor)
        return resposta

    for modulo in (auth, eu, mercado, admin, publico):
        app.include_router(modulo.rotas)
    app.add_api_websocket_route("/api/ws", rota_ws)
    return app
