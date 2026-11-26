"""Contador de limites no Redis (compartilhado entre processos da API)."""

from __future__ import annotations

from typing import Any


class ContadorRedis:  # pragma: no cover - testado na integração
    def __init__(self, redis: Any, prefixo: str = "limite:") -> None:
        self._redis = redis
        self._prefixo = prefixo

    async def incrementar(self, chave: str, janela_s: int) -> int:
        k = self._prefixo + chave
        async with self._redis.pipeline(transaction=True) as p:
            p.incr(k)
            p.expire(k, janela_s, nx=True)
            n, _ = await p.execute()
        return int(n)

    async def ler(self, chave: str) -> str | None:
        valor = await self._redis.get(self._prefixo + chave)
        return None if valor is None else str(valor)

    async def gravar(self, chave: str, valor: str, validade_s: int) -> None:
        await self._redis.set(self._prefixo + chave, valor, ex=max(1, validade_s))

    async def apagar(self, chave: str) -> None:
        await self._redis.delete(self._prefixo + chave)
