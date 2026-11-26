"""Supervisão de tarefas de fundo: a fonte de eventos do WebSocket nunca morre calada."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

from sinais.logs import obter_logger

_log = obter_logger(__name__)


async def supervisionar(
    nome: str, fabrica: Callable[[], Coroutine[Any, Any, None]], espera_s: float = 1.0
) -> None:
    """Roda ``fabrica()`` para sempre: se falhar ou terminar, registra e reinicia após
    ``espera_s``. Só o cancelamento (desligamento do app) encerra."""
    while True:
        try:
            await fabrica()
            _log.error("supervisao.terminou", extra={"campos": {"tarefa": nome}})
        except asyncio.CancelledError:
            raise
        except Exception as erro:
            _log.error(
                "supervisao.falhou",
                extra={"campos": {"tarefa": nome, "erro": type(erro).__name__}},
            )
        await asyncio.sleep(espera_s)
