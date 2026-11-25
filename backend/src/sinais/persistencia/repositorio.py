"""Porta de persistência de candles."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from sinais.core.tempo import InstanteMs
from sinais.dados.modelos import Candle, IntervaloColeta
from sinais.dados.qualidade import Lacuna

type EventoQualidade = tuple[str, str, InstanteMs, InstanteMs, str]


class RepositorioCandles(Protocol):
    async def inserir(self, candles: Sequence[Candle]) -> int:
        """Grava candles fechados. Devolve quantos eram novos (duplicados são ignorados)."""
        ...

    async def ultima_abertura(
        self, simbolo: str, intervalo: IntervaloColeta
    ) -> InstanteMs | None: ...

    async def listar(
        self, simbolo: str, intervalo: IntervaloColeta, inicio: InstanteMs, fim: InstanteMs
    ) -> list[Candle]:
        """Candles com abertura em ``[inicio, fim)``, em ordem."""
        ...

    async def registrar_qualidade(
        self, simbolo: str, intervalo: IntervaloColeta, lacuna: Lacuna, tipo: str
    ) -> None: ...

    async def eventos_qualidade(self, simbolo: str) -> list[EventoQualidade]: ...
