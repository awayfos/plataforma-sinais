"""Última análise ao vivo por símbolo (JSON da ``Analise`` do contrato)."""

from __future__ import annotations

from typing import Any, Protocol

CHAVE = "analise:ultima:{simbolo}"


class ArmazemAnalises(Protocol):
    async def salvar(self, simbolo: str, analise_json: str) -> None: ...

    async def obter(self, simbolo: str) -> str | None: ...


class ArmazemAnalisesMemoria:
    def __init__(self) -> None:
        self._dados: dict[str, str] = {}

    async def salvar(self, simbolo: str, analise_json: str) -> None:
        self._dados[simbolo] = analise_json

    async def obter(self, simbolo: str) -> str | None:
        return self._dados.get(simbolo)


class ArmazemAnalisesRedis:  # pragma: no cover - testado na integração
    def __init__(self, redis: Any) -> None:
        self._redis = redis

    async def salvar(self, simbolo: str, analise_json: str) -> None:
        await self._redis.set(CHAVE.format(simbolo=simbolo), analise_json)

    async def obter(self, simbolo: str) -> str | None:
        valor = await self._redis.get(CHAVE.format(simbolo=simbolo))
        if valor is None:
            return None
        return valor.decode() if isinstance(valor, bytes) else str(valor)
