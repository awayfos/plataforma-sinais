import asyncio
import json
from collections.abc import Callable
from decimal import Decimal

import pytest

pytest.importorskip("httpx")

import httpx  # noqa: E402

from sinais.dados.modelos import IntervaloColeta  # noqa: E402
from sinais.dados.provedores.binance.parsing import ErroParsing  # noqa: E402
from sinais.dados.provedores.binance.rest import ClienteRestBinance, ErroLimiteTaxa  # noqa: E402

T0 = 1795575600000
M = 60_000


def linha(i: int) -> list[object]:
    t = T0 + i * M
    return [t, "100", "110", "90", "105", "1.5", t + M - 1, "157.5", 7, "0.5", "52.5", "0"]


def cliente(
    handler: Callable[[httpx.Request], httpx.Response],
) -> tuple[ClienteRestBinance, list[float]]:
    esperas: list[float] = []

    async def dormir(s: float) -> None:
        esperas.append(s)

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return ClienteRestBinance("https://api.binance.com", http, dormir=dormir), esperas


def test_hora_servidor() -> None:
    c, _ = cliente(lambda r: httpx.Response(200, json={"serverTime": T0}))
    assert asyncio.run(c.hora_servidor()) == T0


def test_klines_parseia_pagina() -> None:
    c, _ = cliente(lambda r: httpx.Response(200, json=[linha(0), linha(1)]))
    velas = asyncio.run(c.klines("BTCUSDT", IntervaloColeta.M1, T0, T0 + 2 * M))
    assert [v.abertura for v in velas] == [T0, T0 + M]
    assert velas[0].fechamento == Decimal("105")


def test_klines_parametros() -> None:
    vistos: list[httpx.Request] = []

    def h(r: httpx.Request) -> httpx.Response:
        vistos.append(r)
        return httpx.Response(200, json=[])

    c, _ = cliente(h)
    asyncio.run(c.klines("ETHUSDT", IntervaloColeta.S1, T0, T0 + 5000, limite=5))
    [r] = vistos
    assert r.url.path == "/api/v3/klines"
    assert dict(r.url.params) == {
        "symbol": "ETHUSDT",
        "interval": "1s",
        "startTime": str(T0),
        "endTime": str(T0 + 4999),
        "limit": "5",
    }


def test_429_respeita_retry_after() -> None:
    respostas = iter(
        [httpx.Response(429, headers={"Retry-After": "7"}), httpx.Response(200, json=[linha(0)])]
    )
    c, esperas = cliente(lambda r: next(respostas))
    velas = asyncio.run(c.klines("BTCUSDT", IntervaloColeta.M1, T0, T0 + M))
    assert len(velas) == 1
    assert esperas == [7.0]


def test_418_levanta_erro_limite() -> None:
    c, _ = cliente(lambda r: httpx.Response(418, headers={"Retry-After": "120"}))
    with pytest.raises(ErroLimiteTaxa) as exc:
        asyncio.run(c.klines("BTCUSDT", IntervaloColeta.M1, T0, T0 + M))
    assert exc.value.espera_s == 120.0


def test_5xx_tenta_de_novo_e_desiste_apos_5() -> None:
    chamadas: list[int] = []

    def h(r: httpx.Request) -> httpx.Response:
        chamadas.append(1)
        return httpx.Response(503)

    c, esperas = cliente(h)
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(c.klines("BTCUSDT", IntervaloColeta.M1, T0, T0 + M))
    assert len(chamadas) == 5
    assert len(esperas) == 4


def test_falha_de_rede_tenta_de_novo() -> None:
    estado = {"n": 0}

    def h(r: httpx.Request) -> httpx.Response:
        estado["n"] += 1
        if estado["n"] == 1:
            raise httpx.ConnectError("caiu")
        return httpx.Response(200, json=[])

    c, esperas = cliente(h)
    assert asyncio.run(c.klines("BTCUSDT", IntervaloColeta.M1, T0, T0 + M)) == []
    assert len(esperas) == 1


def test_linha_malformada_falha_pagina_inteira() -> None:
    ruim = linha(1)
    ruim[2] = "abc"
    c, _ = cliente(lambda r: httpx.Response(200, content=json.dumps([linha(0), ruim])))
    with pytest.raises(ErroParsing):
        asyncio.run(c.klines("BTCUSDT", IntervaloColeta.M1, T0, T0 + 2 * M))


def test_agg_trades_pagina_por_id_ate_o_fim() -> None:
    pedidos: list[dict[str, str]] = []

    def handler(r: httpx.Request) -> httpx.Response:
        q = dict(r.url.params)
        pedidos.append(q)
        assert r.url.path == "/api/v3/aggTrades"
        inicio_id = int(q.get("fromId", "1"))
        itens = [
            {"a": i, "p": "100", "q": "1", "f": i, "l": i, "T": T0 + i, "m": False, "M": True}
            for i in range(inicio_id, min(inicio_id + int(q["limit"]), 6))
        ]
        return httpx.Response(200, json=itens)

    c, _ = cliente(handler)
    negocios = asyncio.run(c.agg_trades("BTCUSDT", T0, T0 + 4, limite=2))
    assert [n.id for n in negocios] == [1, 2, 3]  # o 4 já está fora de [inicio, fim)
    assert pedidos[0]["startTime"] == str(T0) and pedidos[0]["endTime"] == str(T0 + 3)
    assert pedidos[1] == {"symbol": "BTCUSDT", "fromId": "3", "limit": "2"}
