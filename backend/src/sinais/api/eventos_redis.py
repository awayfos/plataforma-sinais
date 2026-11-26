"""Leitura do Redis Streams para o fan-out do WebSocket (uma leitura por processo da API)."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine, Sequence
from typing import Any

from sinais.api.servicos import FonteEventos, Servicos
from sinais.api.sinais_ao_vivo import BuscaCampeao
from sinais.api.velas import GestorVelas
from sinais.api.ws_canais import Distribuidor, traduzir_evento
from sinais.dados.negocios import ErroNegocio, de_payload
from sinais.eventos.contratos import STREAM_ANALISE_ATUALIZADA, STREAM_CANDLE_FECHADO
from sinais.logs import obter_logger

_log = obter_logger(__name__)


def distribuir_resposta(
    resposta: Sequence[tuple[str, Sequence[tuple[str, Any]]]] | None,
    ultimos: dict[str, str],
    distribuidor: Distribuidor,
    campeao: BuscaCampeao | None,
) -> int:
    """Entrega cada entrada de um XREAD; uma entrada ruim é registrada e pulada, nunca
    derruba as outras. Devolve quantas mensagens saíram para os canais."""
    entregues = 0
    for stream, entradas in resposta or []:
        for id_, campos in entradas:
            ultimos[stream] = id_
            try:
                for canal, dados in traduzir_evento(stream, campos, campeao):
                    distribuidor.publicar(canal, dados)
                    entregues += 1
            except Exception as erro:
                _log.error(
                    "api.evento_invalido",
                    extra={"campos": {"stream": stream, "id": id_, "erro": type(erro).__name__}},
                )
    return entregues


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
            distribuir_resposta(resposta, ultimos, s.distribuidor, s.campeao)
            if s.velas is not None:
                for stream, entradas in resposta or []:
                    if stream != STREAM_CANDLE_FECHADO:
                        continue
                    for _, campos in entradas:
                        try:
                            await s.velas.ao_fechado(campos)
                        except Exception as erro:
                            _log.error(
                                "api.vela_fechamento_falhou",
                                extra={"campos": {"erro": type(erro).__name__}},
                            )

    return ler


def fonte_ticks(
    redis: Any, velas: GestorVelas
) -> Callable[[], Coroutine[Any, Any, None]]:  # pragma: no cover - CI
    """Assina ``ticks:*`` no Pub/Sub e entrega cada negócio à vela em formação."""

    async def ouvir() -> None:
        pubsub = redis.pubsub()
        await pubsub.psubscribe("ticks:*")
        try:
            async for msg in pubsub.listen():
                if msg.get("type") != "pmessage":
                    continue
                try:
                    simbolo, n = de_payload(msg["data"])
                except ErroNegocio as erro:
                    _log.error("api.tick_invalido", extra={"campos": {"erro": str(erro)}})
                    continue
                velas.ao_negocio(simbolo, n)
        finally:
            await pubsub.aclose()

    return ouvir
