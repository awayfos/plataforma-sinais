import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest

from sinais.core.tempo import RelogioFixo
from sinais.dados.modelos import IntervaloColeta
from sinais.dados.provedores.binance.streams import (
    ConsumidorStreams,
    nomes_streams,
    url_combinada,
)

T0 = 1795575600000


def test_nomes_streams() -> None:
    nomes = nomes_streams(["BTCUSDT", "ETHUSDT"], [IntervaloColeta.S1, IntervaloColeta.M1])
    assert nomes == [
        "btcusdt@kline_1s",
        "btcusdt@kline_1m",
        "ethusdt@kline_1s",
        "ethusdt@kline_1m",
    ]


def test_limite_1024() -> None:
    simbolos = [f"S{i}USDT" for i in range(513)]
    with pytest.raises(ValueError):
        nomes_streams(simbolos, [IntervaloColeta.S1, IntervaloColeta.M1])


def test_url_combinada() -> None:
    url = url_combinada("wss://data-stream.binance.vision/", ["a@x", "b@y"])
    assert url == "wss://data-stream.binance.vision/stream?streams=a@x/b@y"


class Roteiro:
    """Conector falso: cada conexão entrega uma lista de mensagens ou levanta um erro."""

    def __init__(
        self, conexoes: list[list[str] | Exception], relogio: RelogioFixo, avanco_ms: int = 0
    ) -> None:
        self.conexoes = conexoes
        self.abertas = 0
        self.relogio = relogio
        self.avanco_ms = avanco_ms

    def __call__(self, url: str):  # type: ignore[no-untyped-def]
        @asynccontextmanager
        async def cm() -> AsyncIterator[AsyncIterator[str]]:
            if self.abertas >= len(self.conexoes):
                await asyncio.sleep(3600)
            item = self.conexoes[self.abertas]
            self.abertas += 1
            if isinstance(item, Exception):
                raise item

            async def gerar() -> AsyncIterator[str]:
                for m in item:
                    self.relogio.avancar(self.avanco_ms)
                    yield m

            yield gerar()

        return cm()


def rodar(
    roteiro: Roteiro, relogio: RelogioFixo, ate: int, renovar_apos_ms: int = 85_800_000
) -> tuple[list[str], list[float]]:
    eventos: list[str] = []
    esperas: list[float] = []
    parar = asyncio.Event()

    async def ao_mensagem(m: str) -> None:
        eventos.append(m)
        if sum(1 for e in eventos if not e.startswith("<")) >= ate:
            parar.set()

    async def ao_reconectar() -> None:
        eventos.append("<reconectou>")

    async def dormir(s: float) -> None:
        esperas.append(s)

    c = ConsumidorStreams(
        "wss://x/stream",
        roteiro,
        relogio,
        ao_mensagem,
        ao_reconectar,
        dormir=dormir,
        aleatorio=lambda: 1.0,
        renovar_apos_ms=renovar_apos_ms,
    )

    async def principal() -> None:
        await asyncio.wait_for(c.executar(parar), timeout=5)

    asyncio.run(principal())
    return eventos, esperas


def test_repassa_mensagens() -> None:
    r = RelogioFixo(T0)
    eventos, _ = rodar(Roteiro([["a", "b"]], r), r, ate=2)
    assert eventos == ["<reconectou>", "a", "b"]


def test_reconecta_apos_erro_com_backoff() -> None:
    r = RelogioFixo(T0)
    roteiro = Roteiro([OSError("x"), OSError("y"), ["a"]], r)
    eventos, esperas = rodar(roteiro, r, ate=1)
    assert esperas == [1.0, 2.0]
    assert eventos == ["<reconectou>", "a"]


def test_chama_ao_reconectar_antes_das_novas_mensagens() -> None:
    r = RelogioFixo(T0)
    eventos, _ = rodar(Roteiro([["a"], ["b"]], r), r, ate=2)
    assert eventos == ["<reconectou>", "a", "<reconectou>", "b"]


def test_tentativas_zeram_apos_mensagem() -> None:
    r = RelogioFixo(T0)
    roteiro = Roteiro([OSError("x"), ["a"], OSError("y"), ["b"]], r)
    _, esperas = rodar(roteiro, r, ate=2)
    assert esperas == [1.0, 1.0]


def test_renova_conexao_antes_de_24h() -> None:
    r = RelogioFixo(T0)
    roteiro = Roteiro([["a", "b", "c"], ["d"]], r, avanco_ms=3_600_000)
    eventos, _ = rodar(roteiro, r, ate=3, renovar_apos_ms=2 * 3_600_000)
    assert eventos == ["<reconectou>", "a", "b", "<reconectou>", "d"]
    assert roteiro.abertas == 2


def test_para_quando_evento_parar() -> None:
    r = RelogioFixo(T0)
    eventos, _ = rodar(Roteiro([["a", "b", "c"]], r), r, ate=1)
    assert eventos == ["<reconectou>", "a"]


def test_sincroniza_ja_na_primeira_conexao() -> None:
    """Candles que fecham entre a carga inicial e a primeira conexão não podem se perder."""
    r = RelogioFixo(T0)
    eventos, _ = rodar(Roteiro([["a"]], r), r, ate=1)
    assert eventos[0] == "<reconectou>"


def test_bloqueio_418_respeita_espera() -> None:
    from sinais.dados.provedores.binance.rest import ErroLimiteTaxa

    r = RelogioFixo(T0)
    esperas: list[float] = []
    chamadas = {"n": 0}
    parar = asyncio.Event()

    async def ao_reconectar() -> None:
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            raise ErroLimiteTaxa(300.0)

    async def ao_mensagem(m: str) -> None:
        parar.set()

    async def dormir(s: float) -> None:
        esperas.append(s)

    c = ConsumidorStreams(
        "wss://x",
        Roteiro([["a"], ["b"]], r),
        r,
        ao_mensagem,
        ao_reconectar,
        dormir=dormir,
        aleatorio=lambda: 1.0,
    )
    asyncio.run(asyncio.wait_for(c.executar(parar), 5))
    assert esperas == [300.0]
