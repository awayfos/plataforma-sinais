"""Agregação de candles de 1 min em tempos gráficos maiores.

Só blocos completos e contíguos viram candle: um minuto faltando descarta o bloco,
para nunca apresentar um candle incompleto como fechado.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from sinais.core.dominio import TempoGrafico, abertura_candle
from sinais.dados.modelos import Candle

_MINUTO_MS = 60_000


def _combinar(bloco: Sequence[Candle], tg: TempoGrafico, abertura: int) -> Candle:
    return Candle(
        simbolo=bloco[0].simbolo,
        intervalo_ms=tg.duracao_ms,
        abertura=abertura,
        abertura_preco=bloco[0].abertura_preco,
        maxima=max(c.maxima for c in bloco),
        minima=min(c.minima for c in bloco),
        fechamento=bloco[-1].fechamento,
        volume=sum((c.volume for c in bloco), start=Decimal(0)),
        volume_cotacao=sum((c.volume_cotacao for c in bloco), start=Decimal(0)),
        negocios=sum(c.negocios for c in bloco),
        volume_compra_agressora=sum((c.volume_compra_agressora for c in bloco), start=Decimal(0)),
        fonte="agregado",
    )


def _completo(bloco: Sequence[Candle], tg: TempoGrafico, abertura: int) -> bool:
    n = tg.duracao_ms // _MINUTO_MS
    return len(bloco) == n and all(
        c.abertura == abertura + i * _MINUTO_MS for i, c in enumerate(bloco)
    )


def agregar(candles_1m: Sequence[Candle], tg: TempoGrafico) -> list[Candle]:
    """Agrega uma série ordenada de candles de 1 min. Blocos incompletos são omitidos."""
    blocos: dict[int, list[Candle]] = {}
    for c in candles_1m:
        if c.intervalo_ms != _MINUTO_MS:
            raise ValueError("agregar espera candles de 1 min")
        blocos.setdefault(abertura_candle(c.abertura, tg), []).append(c)
    return [_combinar(b, tg, ab) for ab, b in sorted(blocos.items()) if _completo(b, tg, ab)]


class AgregadorIncremental:
    """Recebe candles de 1 min fechados, em ordem, e emite o candle maior quando o bloco fecha."""

    def __init__(self, tg: TempoGrafico) -> None:
        self._tg = tg
        self._abertura: int | None = None
        self._bloco: list[Candle] = []

    def adicionar(self, c: Candle) -> Candle | None:
        abertura = abertura_candle(c.abertura, self._tg)
        if abertura != self._abertura:
            self._abertura, self._bloco = abertura, []
        self._bloco.append(c)
        if c.fechamento_ms == abertura + self._tg.duracao_ms:
            bloco, self._bloco = self._bloco, []
            if _completo(bloco, self._tg, abertura):
                return _combinar(bloco, self._tg, abertura)
        return None
