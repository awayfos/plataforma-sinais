"""Processo de ticks: aggTrade da Binance → Redis Pub/Sub ``ticks:{SIMBOLO}``.

Não grava nada: os candles persistidos continuam vindo só dos klines fechados do coletor. Usa
o mesmo consumidor de streams (reconexão com backoff, renovação antes de 24 h). Em toda
(re)conexão, antes de ler o stream, republica pelo REST os aggTrades do minuto atual: a vela
em formação na API descarta os repetidos pelo id e não fica com buraco depois de uma queda.

Execução: ``python -m sinais.processos.ticks_binance``.
"""

from __future__ import annotations

import asyncio
import signal
from collections.abc import Awaitable, Callable, Sequence
from typing import Protocol

from sinais.core.tempo import InstanteMs, Relogio
from sinais.dados.negocios import ErroNegocio, canal_ticks, de_agg_trade_ws, para_payload
from sinais.dados.vela_formacao import Negocio
from sinais.logs import obter_logger

_log = obter_logger(__name__)
_M = 60_000

type Publicar = Callable[[str, str], Awaitable[None]]


class FonteNegocios(Protocol):
    async def agg_trades(
        self, simbolo: str, inicio: InstanteMs, fim: InstanteMs
    ) -> list[Negocio]: ...


def nomes_streams_negocios(simbolos: Sequence[str]) -> list[str]:
    return [f"{s.lower()}@aggTrade" for s in simbolos]


class ColetorTicks:
    def __init__(
        self, simbolos: Sequence[str], publicar: Publicar, rest: FonteNegocios, relogio: Relogio
    ) -> None:
        self._simbolos = list(simbolos)
        self._publicar = publicar
        self._rest = rest
        self._relogio = relogio

    async def ao_mensagem(self, texto: str) -> None:
        try:
            lido = de_agg_trade_ws(texto)
        except ErroNegocio as erro:
            _log.error("ticks.mensagem_invalida", extra={"campos": {"erro": str(erro)}})
            return
        if lido is None:
            return
        simbolo, n = lido
        await self._publicar(canal_ticks(simbolo), para_payload(simbolo, n))

    async def ao_reconectar(self) -> None:
        agora = self._relogio.agora_ms()
        inicio = agora - agora % _M
        for simbolo in self._simbolos:
            try:
                negocios = await self._rest.agg_trades(simbolo, inicio, agora + 1)
            except Exception as erro:
                _log.error(
                    "ticks.ressincronizacao_falhou",
                    extra={"campos": {"simbolo": simbolo, "erro": repr(erro)}},
                )
                continue
            for n in negocios:
                await self._publicar(canal_ticks(simbolo), para_payload(simbolo, n))
            _log.info(
                "ticks.ressincronizado", extra={"campos": {"simbolo": simbolo, "n": len(negocios)}}
            )


async def principal() -> None:  # pragma: no cover - ligação de I/O
    import httpx
    from redis.asyncio import Redis

    from sinais.core.config import carregar_configuracao
    from sinais.core.dominio import ATIVOS_V1
    from sinais.core.tempo import RelogioSistema
    from sinais.dados.provedores.binance.rest import ClienteRestBinance
    from sinais.dados.provedores.binance.streams import (
        ConsumidorStreams,
        conector_websockets,
        url_combinada,
    )
    from sinais.logs import configurar_logs

    cfg = carregar_configuracao()
    configurar_logs(cfg.nivel_log)
    simbolos = [a.simbolo_provedor for a in ATIVOS_V1]
    redis = Redis.from_url(cfg.redis_url.get_secret_value(), decode_responses=True)
    parar = asyncio.Event()
    laco = asyncio.get_running_loop()
    for sinal in (signal.SIGTERM, signal.SIGINT):
        laco.add_signal_handler(sinal, parar.set)

    async def publicar(canal: str, texto: str) -> None:
        await redis.publish(canal, texto)

    relogio = RelogioSistema()
    async with httpx.AsyncClient() as http:
        coletor = ColetorTicks(
            simbolos, publicar, ClienteRestBinance(cfg.binance_rest_url, http), relogio
        )
        url = url_combinada(cfg.binance_ws_url, nomes_streams_negocios(simbolos))
        _log.info("ticks.iniciando", extra={"campos": {"simbolos": simbolos}})
        await ConsumidorStreams(
            url, conector_websockets, relogio, coletor.ao_mensagem, coletor.ao_reconectar
        ).executar(parar)
    await redis.aclose()


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(principal())
