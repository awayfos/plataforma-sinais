"""Publicador em memória (dublê de testes)."""

from __future__ import annotations

from collections.abc import Mapping


class PublicadorMemoria:
    def __init__(self) -> None:
        self.publicados: list[tuple[str, dict[str, str]]] = []

    async def publicar(self, stream: str, campos: Mapping[str, str]) -> None:
        self.publicados.append((stream, dict(campos)))
