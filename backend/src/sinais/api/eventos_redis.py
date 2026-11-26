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
from sinais.eventos.ticks_recentes import ler_recentes
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


async def reproduzir_recentes(redis: Any, velas: GestorVelas) -> int:
    """Relê ``ticks.recentes:{SIMBOLO}`` (minuto atual e anterior) e entrega à vela. Devolve
    quantos negócios foram lidos; repetidos são descartados pela própria vela (id)."""
    lidos = 0
    for simbolo in velas.simbolos:
        try:
            textos = await ler_recentes(redis, simbolo)
        except Exception as erro:
            _log.error(
                "api.ticks_recentes_falhou",
                extra={"campos": {"simbolo": simbolo, "erro": type(erro).__name__}},
            )
            continue
        for texto in textos:
            try:
                s, n = de_payload(texto)
            except ErroNegocio:
                continue
            velas.ao_negocio(s, n)
            lidos += 1
    return lidos


def fonte_ticks(redis: Any, velas: GestorVelas) -> Callable[[], Coroutine[Any, Any, None]]:
    """Assina ``ticks:*`` no Pub/Sub e entrega cada negócio à vela em formação.

    A cada confirmação de assinatura (subida da API, reconexão do Pub/Sub ou reinício pela
    supervisão) relê os negócios recentes guardados pelo processo de ticks antes de seguir ao
    vivo: o que foi publicado enquanto ninguém ouvia não se perde."""

    async def ouvir() -> None:
        pubsub = redis.pubsub()
        await pubsub.psubscribe("ticks:*")
        try:
            async for msg in pubsub.listen():
                tipo = msg.get("type")
                if tipo == "psubscribe":
                    lidos = await reproduzir_recentes(redis, velas)
                    _log.info("api.ticks_ressincronizados", extra={"campos": {"n": lidos}})
                    continue
                if tipo != "pmessage":
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
