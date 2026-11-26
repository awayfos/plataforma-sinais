"""Cenários sintéticos de 1m para os detectores de situações (nunca dados reais)."""

import numpy as np
import pandas as pd

from ..analise.sinteticos import T0

M = 60_000


def minutos(
    c: list[float] | np.ndarray,
    h: list[float] | np.ndarray | None = None,
    lo: list[float] | np.ndarray | None = None,
    o: list[float] | np.ndarray | None = None,
    v: list[float] | np.ndarray | float = 10.0,
    pressao: list[float] | np.ndarray | float = 0.5,
    t0: int = T0,
) -> pd.DataFrame:
    """Candles de 1m; sem ``h``/``lo``, pavios de 0,1 acima e abaixo do corpo."""
    c = np.asarray(c, dtype="float64")
    n = len(c)
    o = np.concatenate([[c[0]], c[:-1]]) if o is None else np.asarray(o, dtype="float64")
    h = np.maximum(o, c) + 0.1 if h is None else np.asarray(h, dtype="float64")
    lo = np.minimum(o, c) - 0.1 if lo is None else np.asarray(lo, dtype="float64")
    v = np.broadcast_to(np.asarray(v, dtype="float64"), (n,)).copy()
    p = np.broadcast_to(np.asarray(pressao, dtype="float64"), (n,))
    idx = pd.Index(t0 + np.arange(n) * M, name="abertura")
    return pd.DataFrame({"o": o, "h": h, "l": lo, "c": c, "v": v, "vb": v * p}, index=idx)


def passeio(n: int, semente: int = 1, passo: float = 0.3, t0: int = T0) -> pd.DataFrame:
    """Passeio com tendências alternadas (a cada 600 min) e pressão aleatória."""
    rng = np.random.default_rng(semente)
    deriva = np.repeat(rng.choice([-0.08, 0.0, 0.08], size=n // 600 + 1), 600)[:n]
    c = 1000 + np.cumsum(rng.normal(0, passo, n) + deriva)
    o = np.concatenate([[c[0]], c[:-1]])
    h = np.maximum(o, c) + rng.exponential(0.15, n)
    lo = np.minimum(o, c) - rng.exponential(0.15, n)
    v = rng.uniform(5, 40, n)
    sinal = np.sign(c - o)
    p = np.clip(0.5 + 0.12 * sinal + rng.normal(0, 0.1, n), 0.02, 0.98)
    return minutos(c, h=h, lo=lo, o=o, v=v, pressao=p, t0=t0)


def espelhar(df: pd.DataFrame, k: float = 2000.0) -> pd.DataFrame:
    """Preço refletido (k − x), máxima ↔ mínima e compra ↔ venda agressora."""
    return pd.DataFrame(
        {
            "o": k - df["o"],
            "h": k - df["l"],
            "l": k - df["h"],
            "c": k - df["c"],
            "v": df["v"],
            "vb": df["v"] - df["vb"],
        },
        index=df.index,
    )
