"""Leitura do Redis Streams para o fan-out do WebSocket (uma leitura por processo da API)."""

from __future__ import annotations

import asyncio
from typing import Any

from sinais.api.servicos import FonteEventos, Servicos
from sinais.api.ws_canais import traduzir_evento
from sinais.eventos.contratos import STREAM_ANALISE_ATUALIZADA, STREAM_CANDLE_FECHADO
from sinais.logs import obter_logger

_log = obter_logger(__name__)


def fonte_redis(redis: Any, bloqueio_ms: int = 5000) -> FonteEventos:  # pragma: no cover - CI
    async def ler(s: Servicos) -> None:
        ultimos: dict[str, str] = {STREAM_CANDLE_FECHADO: "$", STREAM_ANALISE_ATUALIZADA: "$"}
        while True:
            try:
                resposta = await redis.xread(ultimos, count=500, block=bloqueio_ms)
            except asyncio.CancelledError:
                raise
            except Exception as erro:
                _log.error("api.eventos_falhou", extra={"campos": {"erro": repr(erro)}})
                await asyncio.sleep(1)
                continue
            for stream, entradas in resposta or []:
                for id_, campos in entradas:
                    ultimos[stream] = id_
                    for canal, dados in traduzir_evento(stream, campos, s.campeao):
                        s.distribuidor.publicar(canal, dados)

    return ler
