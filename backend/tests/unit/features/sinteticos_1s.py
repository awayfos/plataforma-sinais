"""Séries sintéticas de 1 s para testes (nunca dados reais)."""

import numpy as np
import pandas as pd

from ..analise.sinteticos import T0


def segundos(
    c: list[float] | np.ndarray,
    v: list[float] | np.ndarray | float = 1.0,
    vb: list[float] | np.ndarray | float = 0.5,
    n: float = 2.0,
    t0: int = T0,
) -> pd.DataFrame:
    c = np.asarray(c, dtype="float64")
    o = np.concatenate([[c[0]], c[:-1]])
    idx = pd.Index(t0 + np.arange(len(c)) * 1000, name="abertura")
    df = pd.DataFrame(
        {"o": o, "h": np.maximum(o, c), "l": np.minimum(o, c), "c": c, "v": v, "vb": vb, "n": n},
        index=idx,
    )
    return df.astype("float64")


def passeio_1s(minutos: int, semente: int = 3, t0: int = T0) -> pd.DataFrame:
    """Passeio com preços arredondados a 0,01 (muitos segundos sem mudança) e volume variável."""
    rng = np.random.default_rng(semente)
    k = minutos * 60
    c = np.round(100 + np.cumsum(rng.normal(0, 0.01, k)), 2)
    v = rng.exponential(1.0, k) * (rng.random(k) > 0.2)
    df = segundos(c, v=v, vb=v * rng.uniform(0, 1, k), t0=t0)
    df["n"] = np.where(v > 0, rng.integers(1, 20, k), 0).astype("float64")
    return df


def para_1m(df_1s: pd.DataFrame) -> pd.DataFrame:
    """Candles de 1m coerentes com os segundos (como os klines oficiais)."""
    t = df_1s.index.to_numpy(dtype="int64")
    g = df_1s.groupby(pd.Index(t - t % 60_000, name="abertura"))
    return pd.DataFrame(
        {
            "o": g["o"].first(),
            "h": g["h"].max(),
            "l": g["l"].min(),
            "c": g["c"].last(),
            "v": g["v"].sum(),
            "vb": g["vb"].sum(),
        }
    )
