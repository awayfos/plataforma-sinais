"""Candles sintéticos em sequência para testes de rota."""

from sinais.dados.modelos import Candle

from ..contrato.repositorio_candles import M, vela


def velas(n: int) -> list[Candle]:
    return [vela(i) for i in range(n)]


__all__ = ["M", "velas"]
