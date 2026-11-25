"""Publicador no Redis Streams (XADD com tamanho máximo aproximado)."""

from __future__ import annotations

from collections.abc import Mapping

from redis.asyncio import Redis
from redis.typing import EncodableT, FieldT


class PublicadorRedis:
    def __init__(self, redis: Redis, maxlen: int = 100_000) -> None:
        self._redis = redis
        self._maxlen = maxlen

    async def publicar(self, stream: str, campos: Mapping[str, str]) -> None:
        dados: dict[FieldT, EncodableT] = dict(campos)
        await self._redis.xadd(stream, dados, maxlen=self._maxlen, approximate=True)
