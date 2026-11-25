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
