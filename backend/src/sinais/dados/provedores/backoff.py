"""Backoff exponencial com jitter para novas tentativas e reconexões."""

from __future__ import annotations

import random
from collections.abc import Callable


def atraso_backoff(
    tentativa: int,
    base_s: float = 1.0,
    teto_s: float = 60.0,
    aleatorio: Callable[[], float] = random.random,
) -> float:
    """Atraso para a ``tentativa`` (0 = primeira): entre metade e o total de ``base * 2^n``."""
    total = min(teto_s, base_s * float(2 ** min(tentativa, 30)))
    return total / 2 + (total / 2) * aleatorio()
