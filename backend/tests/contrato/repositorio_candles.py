"""Contrato de ``RepositorioCandles``: os mesmos casos valem para o dublê e para o PostgreSQL."""

import asyncio
from collections.abc import Awaitable, Callable
from decimal import Decimal

from sinais.dados.modelos import Candle, IntervaloColeta
from sinais.dados.qualidade import Lacuna
from sinais.persistencia.repositorio import RepositorioCandles

T0 = 1795575600000
M = 60_000

type Fabrica = Callable[[], Awaitable[RepositorioCandles]]


def vela(i: int, simbolo: str = "BTCUSDT", preco: str = "59194.01") -> Candle:
    p = Decimal(preco)
    return Candle(
        simbolo,
        M,
        T0 + i * M,
        p,
        p + Decimal("0.5"),
        p - Decimal("0.25"),
        p,
        Decimal("1.23456789"),
        Decimal("73080.123456789012"),
        42,
        Decimal("0.5"),
        "binance",
    )


def inserir_e_listar_ida_e_volta(fabrica: Fabrica) -> None:
    async def caso() -> None:
        repo = await fabrica()
        velas = [vela(0), vela(1), vela(2)]
        assert await repo.inserir(velas) == 3
        lidas = await repo.listar("BTCUSDT", IntervaloColeta.M1, T0, T0 + 3 * M)
        assert lidas == velas

    asyncio.run(caso())


def inserir_idempotente(fabrica: Fabrica) -> None:
    async def caso() -> None:
        repo = await fabrica()
        assert await repo.inserir([vela(0), vela(1)]) == 2
        assert await repo.inserir([vela(1), vela(2)]) == 1
        assert len(await repo.listar("BTCUSDT", IntervaloColeta.M1, T0, T0 + 10 * M)) == 3

    asyncio.run(caso())


def ultima_abertura(fabrica: Fabrica) -> None:
    async def caso() -> None:
        repo = await fabrica()
        assert await repo.ultima_abertura("BTCUSDT", IntervaloColeta.M1) is None
        await repo.inserir([vela(0), vela(5), vela(3), vela(9, simbolo="ETHUSDT")])
        assert await repo.ultima_abertura("BTCUSDT", IntervaloColeta.M1) == T0 + 5 * M

    asyncio.run(caso())


def listar_filtra_intervalo_e_simbolo(fabrica: Fabrica) -> None:
    async def caso() -> None:
        repo = await fabrica()
        await repo.inserir([vela(i) for i in range(5)] + [vela(1, simbolo="ETHUSDT")])
        lidas = await repo.listar("BTCUSDT", IntervaloColeta.M1, T0 + M, T0 + 3 * M)
        assert [c.abertura for c in lidas] == [T0 + M, T0 + 2 * M]

    asyncio.run(caso())


def registrar_qualidade(fabrica: Fabrica) -> None:
    async def caso() -> None:
        repo = await fabrica()
        await repo.registrar_qualidade("BTCUSDT", IntervaloColeta.M1, Lacuna(T0, T0 + M), "lacuna")
        eventos = await repo.eventos_qualidade("BTCUSDT")
        assert eventos == [("BTCUSDT", "1m", T0, T0 + M, "lacuna")]

    asyncio.run(caso())


CASOS = [
    inserir_e_listar_ida_e_volta,
    inserir_idempotente,
    ultima_abertura,
    listar_filtra_intervalo_e_simbolo,
    registrar_qualidade,
]
