import asyncio

import pytest

pytest.importorskip("websockets")

from websockets.asyncio.server import ServerConnection, serve  # noqa: E402

from sinais.dados.provedores.binance.streams import conector_websockets  # noqa: E402


def test_adaptador_recebe_do_servidor_local() -> None:
    async def enviar(ws: ServerConnection) -> None:
        await ws.send("um")
        await ws.send(b"dois")

    async def principal() -> list[str]:
        async with serve(enviar, "127.0.0.1", 0) as servidor:
            porta = next(iter(servidor.sockets)).getsockname()[1]
            recebidas: list[str] = []
            async with conector_websockets(f"ws://127.0.0.1:{porta}") as mensagens:
                async for m in mensagens:
                    recebidas.append(m)
            return recebidas

    assert asyncio.run(asyncio.wait_for(principal(), 10)) == ["um", "dois"]
