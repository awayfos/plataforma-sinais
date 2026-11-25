"""Contratos dos eventos publicados no Redis Streams (design §10)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from sinais.dados.modelos import Candle

STREAM_CANDLE_FECHADO = "candle.fechado"
STREAM_ANALISE_ATUALIZADA = "analise.atualizada"
VERSAO = "1"


class Publicador(Protocol):
    async def publicar(self, stream: str, campos: Mapping[str, str]) -> None: ...


def evento_candle_fechado(c: Candle) -> dict[str, str]:
    """Campos em texto. Preços mantêm a representação decimal exata da fonte."""
    return {
        "versao": VERSAO,
        "id": f"{c.simbolo}:{c.intervalo_ms}:{c.abertura}",
        "simbolo": c.simbolo,
        "intervalo_ms": str(c.intervalo_ms),
        "abertura": str(c.abertura),
        "o": str(c.abertura_preco),
        "h": str(c.maxima),
        "l": str(c.minima),
        "c": str(c.fechamento),
        "v": str(c.volume),
        "fonte": c.fonte,
    }


def evento_analise_atualizada(simbolo: str, t: int, analise_json: str) -> dict[str, str]:
    """``analise`` leva a ``Analise`` do contrato da API serializada em JSON."""
    return {
        "versao": VERSAO,
        "id": f"{simbolo}:{t}",
        "simbolo": simbolo,
        "t": str(t),
        "analise": analise_json,
    }
