import asyncio

import pytest

pytest.importorskip("redis")

from redis.asyncio import Redis  # noqa: E402

from sinais.eventos.redis_streams import PublicadorRedis  # noqa: E402

from .conftest import exigir_redis  # noqa: E402

pytestmark = pytest.mark.integracao


def test_xadd_e_leitura_por_grupo() -> None:
    url = exigir_redis()

    async def caso() -> list[dict[str, str]]:
        r = Redis.from_url(url, decode_responses=True)
        await r.delete("teste.stream")
        await PublicadorRedis(r).publicar("teste.stream", {"id": "x:1", "c": "1.5"})
        await r.xgroup_create("teste.stream", "g1", id="0")
        resp = await r.xreadgroup("g1", "c1", {"teste.stream": ">"}, count=10)
        await r.aclose()
        return [campos for _, entradas in resp for _, campos in entradas]

    assert asyncio.run(caso()) == [{"id": "x:1", "c": "1.5"}]


def test_api_que_sobe_no_meio_do_minuto_rele_os_negocios_recentes() -> None:
    """Redis real: o processo de ticks grava e publica; uma API que só assina depois relê o
    stream curto e monta a vela com O/H/L/V do minuto inteiro (e segue ao vivo)."""
    from decimal import Decimal

    from sinais.api.eventos_redis import fonte_ticks
    from sinais.api.velas import GestorVelas
    from sinais.api.ws_canais import Distribuidor
    from sinais.core.tempo import RelogioSistema
    from sinais.dados.negocios import canal_ticks, para_payload
    from sinais.dados.vela_formacao import Negocio
    from sinais.eventos.ticks_recentes import PublicadorTicksRedis, chave_recentes
    from sinais.persistencia.memoria import RepositorioCandlesMemoria

    url = exigir_redis()
    simbolo = "TESTEUSDT"

    async def caso() -> dict[str, object] | None:
        r = Redis.from_url(url, decode_responses=True)
        await r.delete(chave_recentes(simbolo))
        relogio = RelogioSistema()
        agora = relogio.agora_ms()
        t0 = agora - agora % 60_000
        pub = PublicadorTicksRedis(r, relogio)
        negocios = [
            Negocio(1, Decimal("100"), Decimal("2"), t0 + 1, False),
            Negocio(2, Decimal("120"), Decimal("1"), t0 + 2, False),
            Negocio(3, Decimal("90"), Decimal("1"), t0 + 3, True),
        ]
        for n in negocios:  # ninguém ouvindo
            await pub(canal_ticks(simbolo), para_payload(simbolo, n))
        assert 0 < await r.pttl(chave_recentes(simbolo)) <= 180_000
        velas = GestorVelas([simbolo], RepositorioCandlesMemoria(), relogio, Distribuidor())
        tarefa = asyncio.create_task(fonte_ticks(r, velas)())
        for _ in range(100):
            await asyncio.sleep(0.05)
            if velas.snapshot(f"candles:{simbolo}:1m") is not None:
                break
        # ao vivo depois da releitura (o repetido sai pelo id)
        for n in (negocios[2], Negocio(4, Decimal("95"), Decimal("1"), t0 + 4, False)):
            await pub(canal_ticks(simbolo), para_payload(simbolo, n))
        for _ in range(100):
            await asyncio.sleep(0.05)
            if (velas.snapshot(f"candles:{simbolo}:1m") or {}).get("c") == "95":
                break
        tarefa.cancel()
        await asyncio.gather(tarefa, return_exceptions=True)
        await r.delete(chave_recentes(simbolo))
        await r.aclose()
        return velas.snapshot(f"candles:{simbolo}:1m")

    foto = asyncio.run(caso())
    assert foto is not None
    assert {k: foto[k] for k in ("o", "h", "l", "c", "v")} == {
        "o": "100",
        "h": "120",
        "l": "90",
        "c": "95",
        "v": "5",
    }
