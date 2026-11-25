"""Séries sintéticas para testes (nunca dados reais)."""

import numpy as np
import pandas as pd

T0 = 1795575600000
M = 60_000


def quadro(
    fechamentos: list[float] | np.ndarray,
    amplitude: float = 1.0,
    volume: float = 10.0,
    t0: int = T0,
) -> pd.DataFrame:
    c = np.asarray(fechamentos, dtype="float64")
    o = np.concatenate([[c[0]], c[:-1]])
    h = np.maximum(o, c) + amplitude / 2
    lo = np.minimum(o, c) - amplitude / 2
    idx = pd.Index(t0 + np.arange(len(c)) * M, name="abertura")
    return pd.DataFrame({"o": o, "h": h, "l": lo, "c": c, "v": volume, "vb": volume / 2}, index=idx)


def passeio(n: int = 3000, semente: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(semente)
    c = 100 + np.cumsum(rng.normal(0, 0.3, n))
    df = quadro(c, amplitude=0.4)
    df["v"] = rng.uniform(1, 20, n)
    df["vb"] = df["v"] * rng.uniform(0.2, 0.8, n)
    return df
