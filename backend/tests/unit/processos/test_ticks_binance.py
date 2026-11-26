import asyncio
import json
from decimal import Decimal

from sinais.core.tempo import RelogioFixo
from sinais.dados.vela_formacao import Negocio
from sinais.processos.ticks_binance import ColetorTicks, nomes_streams_negocios

T9 = 1795597200000


class RestFalso:
    def __init__(self) -> None:
        self.pedidos: list[tuple[str, int, int]] = []

    async def agg_trades(self, simbolo: str, inicio: int, fim: int) -> list[Negocio]:
        self.pedidos.append((simbolo, inicio, fim))
        return [Negocio(1, Decimal("100"), Decimal("1"), inicio + 5, False)]


def mensagem(a: int, t: int) -> str:
    return json.dumps(
        {
            "stream": "btcusdt@aggTrade",
            "data": {
                "e": "aggTrade",
                "s": "BTCUSDT",
                "a": a,
                "p": "101.5",
                "q": "2",
                "f": a,
                "l": a,
                "T": t,
                "m": False,
                "M": True,
            },
        }
    )


def test_nomes_dos_streams() -> None:
    assert nomes_streams_negocios(["BTCUSDT", "ETHUSDT"]) == [
        "btcusdt@aggTrade",
        "ethusdt@aggTrade",
    ]


def test_publica_cada_negocio_no_canal_do_simbolo_e_ignora_lixo() -> None:
    async def caso() -> list[tuple[str, dict[str, object]]]:
        enviados: list[tuple[str, str]] = []

        async def publicar(canal: str, texto: str) -> None:
            enviados.append((canal, texto))

        c = ColetorTicks(["BTCUSDT"], publicar, RestFalso(), RelogioFixo(T9))
        await c.ao_mensagem(mensagem(7, T9 + 1))
        await c.ao_mensagem("lixo")
        await c.ao_mensagem(json.dumps({"stream": "x", "data": {"e": "kline"}}))
        return [(canal, json.loads(t)) for canal, t in enviados]

    enviados = asyncio.run(caso())
    assert enviados == [
        (
            "ticks:BTCUSDT",
            {
                "versao": "1",
                "simbolo": "BTCUSDT",
                "id": 7,
                "preco": "101.5",
                "qtd": "2",
                "t": T9 + 1,
                "maker": False,
            },
        )
    ]


def test_reconexao_republica_o_minuto_atual_pelo_rest() -> None:
    async def caso() -> tuple[RestFalso, list[str]]:
        enviados: list[str] = []

        async def publicar(canal: str, texto: str) -> None:
            enviados.append(canal)

        rest = RestFalso()
        c = ColetorTicks(["BTCUSDT", "ETHUSDT"], publicar, rest, RelogioFixo(T9 + 42_000))
        await c.ao_reconectar()
        return rest, enviados

    rest, enviados = asyncio.run(caso())
    assert rest.pedidos == [("BTCUSDT", T9, T9 + 42_001), ("ETHUSDT", T9, T9 + 42_001)]
    assert enviados == ["ticks:BTCUSDT", "ticks:ETHUSDT"]


def test_falha_do_rest_na_reconexao_nao_derruba_o_stream() -> None:
    class RestQuebrado:
        async def agg_trades(self, simbolo: str, inicio: int, fim: int) -> list[Negocio]:
            raise RuntimeError("fora")

    async def nada(canal: str, texto: str) -> None:
        return None

    asyncio.run(ColetorTicks(["BTCUSDT"], nada, RestQuebrado(), RelogioFixo(T9)).ao_reconectar())
