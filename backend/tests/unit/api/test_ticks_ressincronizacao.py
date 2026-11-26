"""Ressincronização da vela em formação: reinício da API (ou queda do Pub/Sub) no meio do
minuto não pode deixar O/H/L/V errados. O processo de ticks guarda os negócios recentes num
stream curto por símbolo e a API relê esse stream a cada (re)assinatura antes de seguir ao vivo.
"""

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator
from decimal import Decimal
from typing import Any

from sinais.api.eventos_redis import fonte_ticks
from sinais.api.velas import GestorVelas
from sinais.api.ws_canais import Distribuidor
from sinais.core.tempo import RelogioFixo
from sinais.dados.negocios import canal_ticks, para_payload
from sinais.dados.vela_formacao import Negocio
from sinais.eventos.ticks_recentes import (
    VALIDADE_MS,
    PublicadorTicksRedis,
    chave_recentes,
    inicio_retencao,
)
from sinais.persistencia.memoria import RepositorioCandlesMemoria

M = 60_000
T9 = 1795597200000


class _PubSubFalso:
    def __init__(self, redis: "RedisFalso") -> None:
        self._redis = redis
        self.fila: asyncio.Queue[str | None] = asyncio.Queue()

    async def psubscribe(self, padrao: str) -> None:
        assert padrao == "ticks:*"
        self._redis.ouvintes.append(self)

    async def listen(self) -> AsyncIterator[dict[str, Any]]:
        yield {"type": "psubscribe", "pattern": None, "channel": "ticks:*", "data": 1}
        while True:
            texto = await self.fila.get()
            if texto is None:
                return
            yield {"type": "pmessage", "pattern": "ticks:*", "channel": "x", "data": texto}

    async def aclose(self) -> None:
        if self in self._redis.ouvintes:
            self._redis.ouvintes.remove(self)


class _PipeFalso:
    def __init__(self, redis: "RedisFalso") -> None:
        self._redis = redis
        self._ops: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def publish(self, *a: Any, **k: Any) -> None:
        self._ops.append(("publish", a, k))

    def xadd(self, *a: Any, **k: Any) -> None:
        self._ops.append(("xadd", a, k))

    def pexpire(self, *a: Any, **k: Any) -> None:
        self._ops.append(("pexpire", a, k))

    async def execute(self) -> list[Any]:
        for nome, a, k in self._ops:
            self._redis.comandos.append(nome)
            if nome == "publish":
                for o in list(self._redis.ouvintes):
                    o.fila.put_nowait(a[1])
            elif nome == "xadd":
                self._redis.streams[a[0]].append(dict(a[1]))
                self._redis.minids[a[0]] = k.get("minid")
            else:
                self._redis.validades[a[0]] = a[1]
        return []


class RedisFalso:
    def __init__(self) -> None:
        self.streams: dict[str, list[dict[str, str]]] = defaultdict(list)
        self.minids: dict[str, Any] = {}
        self.validades: dict[str, int] = {}
        self.comandos: list[str] = []
        self.ouvintes: list[_PubSubFalso] = []

    def pubsub(self) -> _PubSubFalso:
        return _PubSubFalso(self)

    def pipeline(self, transaction: bool = True) -> _PipeFalso:
        assert transaction is False
        return _PipeFalso(self)

    async def xrange(self, chave: str) -> list[tuple[str, dict[str, str]]]:
        return [(f"{i}-0", c) for i, c in enumerate(self.streams.get(chave, []))]


def neg(id_: int, seg: int, preco: str, qtd: str = "1") -> Negocio:
    return Negocio(id_, Decimal(preco), Decimal(qtd), T9 + seg * 1000, False)


async def _esperar(condicao: Any) -> None:
    for _ in range(200):
        if condicao():
            return
        await asyncio.sleep(0.005)
    raise AssertionError("condição não atingida")


def test_publicador_grava_o_recente_antes_de_publicar_e_apara_pelo_minuto_anterior() -> None:
    async def caso() -> None:
        r = RedisFalso()
        pub = PublicadorTicksRedis(r, RelogioFixo(T9 + 2 * M + 30_000))
        await pub(canal_ticks("BTCUSDT"), para_payload("BTCUSDT", neg(1, 150, "100")))
        # gravado antes do PUBLISH: quem assinar depois do PUBLISH ainda acha no stream
        assert r.comandos == ["xadd", "publish", "pexpire"]
        assert len(r.streams[chave_recentes("BTCUSDT")]) == 1
        assert r.minids[chave_recentes("BTCUSDT")] == T9 + M
        assert r.validades[chave_recentes("BTCUSDT")] == VALIDADE_MS

    asyncio.run(caso())
    assert inicio_retencao(T9 + 59_999) == T9 - M


def test_api_reiniciada_no_meio_do_minuto_mantem_ohlcv_corretos() -> None:
    async def caso() -> None:
        r = RedisFalso()
        pub = PublicadorTicksRedis(r, RelogioFixo(T9 + 40_000))

        async def publicar(n: Negocio) -> None:
            await pub(canal_ticks("BTCUSDT"), para_payload("BTCUSDT", n))

        # 1ª API ouve os três primeiros negócios do minuto e cai
        velas_a = GestorVelas(
            ["BTCUSDT"], RepositorioCandlesMemoria(), RelogioFixo(T9), Distribuidor()
        )
        tarefa_a = asyncio.create_task(fonte_ticks(r, velas_a)())
        await _esperar(lambda: r.ouvintes)
        for n in (neg(1, 1, "100", "2"), neg(2, 5, "120"), neg(3, 9, "90")):
            await publicar(n)
        await _esperar(lambda: velas_a.snapshot("candles:BTCUSDT:1m") is not None)
        tarefa_a.cancel()
        await asyncio.gather(tarefa_a, return_exceptions=True)
        assert not r.ouvintes

        # negócios enquanto nenhuma API ouvia
        for n in (neg(4, 20, "130", "3"), neg(5, 25, "110")):
            await publicar(n)

        # 2ª API sobe: relê os recentes, depois segue ao vivo (repetido descartado pelo id)
        d = Distribuidor()
        velas_b = GestorVelas(["BTCUSDT"], RepositorioCandlesMemoria(), RelogioFixo(T9), d)
        tarefa_b = asyncio.create_task(fonte_ticks(r, velas_b)())
        await _esperar(lambda: r.ouvintes)
        await publicar(neg(5, 25, "110"))
        await publicar(neg(6, 30, "105"))
        await _esperar(lambda: (velas_b.snapshot("candles:BTCUSDT:1m") or {}).get("c") == "105")
        tarefa_b.cancel()
        await asyncio.gather(tarefa_b, return_exceptions=True)
        assert velas_b.snapshot("candles:BTCUSDT:1m") == {
            "t": T9,
            "o": "100",
            "h": "130",
            "l": "90",
            "c": "105",
            "v": "9",
            "fechado": False,
        }

    asyncio.run(caso())
