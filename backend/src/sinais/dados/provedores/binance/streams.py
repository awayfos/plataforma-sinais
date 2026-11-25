"""Consumo de streams combinados da Binance com reconexão e renovação antes de 24 h."""

from __future__ import annotations

import asyncio
import random
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from sinais.core.tempo import Relogio
from sinais.dados.modelos import IntervaloColeta
from sinais.dados.provedores.backoff import atraso_backoff
from sinais.dados.provedores.erros import ErroLimiteTaxa
from sinais.logs import obter_logger

_log = obter_logger(__name__)
MAX_STREAMS_POR_CONEXAO = 1024
RENOVAR_APOS_MS = 85_800_000  # 23 h 50 min: a Binance derruba a conexão em 24 h

type Conector = Callable[[str], AbstractAsyncContextManager[AsyncIterator[str]]]


def nomes_streams(simbolos: Sequence[str], intervalos: Sequence[IntervaloColeta]) -> list[str]:
    nomes = [f"{s.lower()}@kline_{i.value}" for s in simbolos for i in intervalos]
    if len(nomes) > MAX_STREAMS_POR_CONEXAO:
        raise ValueError(f"{len(nomes)} streams excedem o limite de {MAX_STREAMS_POR_CONEXAO}")
    return nomes


def url_combinada(base: str, streams: Sequence[str]) -> str:
    return f"{base.rstrip('/')}/stream?streams={'/'.join(streams)}"


class ConsumidorStreams:
    def __init__(
        self,
        url: str,
        conectar: Conector,
        relogio: Relogio,
        ao_mensagem: Callable[[str], Awaitable[None]],
        ao_reconectar: Callable[[], Awaitable[None]],
        dormir: Callable[[float], Awaitable[None]] = asyncio.sleep,
        renovar_apos_ms: int = RENOVAR_APOS_MS,
        aleatorio: Callable[[], float] = random.random,
    ) -> None:
        self._url = url
        self._conectar = conectar
        self._relogio = relogio
        self._ao_mensagem = ao_mensagem
        self._ao_reconectar = ao_reconectar
        self._dormir = dormir
        self._renovar_apos_ms = renovar_apos_ms
        self._aleatorio = aleatorio

    async def executar(self, parar: asyncio.Event) -> None:
        """Consome até ``parar`` ser acionado. ``ao_reconectar`` roda antes das mensagens de
        toda conexão, inclusive a primeira: preenche o que fechou enquanto não havia conexão."""
        tentativa = 0
        while not parar.is_set():
            recebidas = 0
            try:
                async with self._conectar(self._url) as mensagens:
                    await self._ao_reconectar()
                    inicio = self._relogio.agora_ms()
                    _log.info("binance.ws.conectado", extra={"campos": {"url": self._url}})
                    async for m in mensagens:
                        recebidas += 1
                        tentativa = 0
                        await self._ao_mensagem(m)
                        if parar.is_set():
                            return
                        if self._relogio.agora_ms() - inicio >= self._renovar_apos_ms:
                            _log.info("binance.ws.renovando")
                            break
            except asyncio.CancelledError:
                raise
            except ErroLimiteTaxa as erro:
                _log.error("binance.bloqueio", extra={"campos": {"espera_s": erro.espera_s}})
                await self._dormir(erro.espera_s)
                continue
            except Exception as erro:
                espera = atraso_backoff(tentativa, aleatorio=self._aleatorio)
                tentativa += 1
                _log.warning(
                    "binance.ws.erro",
                    extra={"campos": {"erro": repr(erro), "espera_s": espera}},
                )
                await self._dormir(espera)
                continue
            if recebidas == 0 and not parar.is_set():
                espera = atraso_backoff(tentativa, aleatorio=self._aleatorio)
                tentativa += 1
                await self._dormir(espera)


def conector_websockets(url: str) -> AbstractAsyncContextManager[AsyncIterator[str]]:
    """Adaptador para a biblioteca ``websockets``. O servidor envia ping; ela responde pong."""
    import websockets

    @asynccontextmanager
    async def cm() -> AsyncIterator[AsyncIterator[str]]:
        async with websockets.connect(url, ping_interval=None, max_size=2**20) as ws:

            async def mensagens() -> AsyncIterator[str]:
                async for m in ws:
                    yield m if isinstance(m, str) else m.decode()

            yield mensagens()

    return cm()
