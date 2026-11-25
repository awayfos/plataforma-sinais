"""Fábrica de candles de teste (dados sintéticos, nunca reais)."""

from decimal import Decimal

from sinais.dados.modelos import Candle

T0 = 1795575600000  # 2026-11-25T03:00:00Z (quarta), alinhado a 5m e 1h
M = 60_000


def c1m(
    i: int,
    o: str = "100",
    h: str = "110",
    l: str = "90",  # noqa: E741
    c: str = "105",
    v: str = "1",
    simbolo: str = "BTCUSDT",
    t0: int = T0,
) -> Candle:
    return Candle(
        simbolo,
        M,
        t0 + i * M,
        Decimal(o),
        Decimal(h),
        Decimal(l),
        Decimal(c),
        Decimal(v),
        Decimal(v) * 100,
        1,
        Decimal(v) / 2,
        "teste",
    )
