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


def de_barras(
    c_barras: list[float] | np.ndarray,
    por_barra: int = 5,
    pavio: float = 0.2,
    t0: int = T0,
    pressao: float = 0.5,
    maximas: dict[int, float] | None = None,
    minimas: dict[int, float] | None = None,
) -> pd.DataFrame:
    """Expande barras (abertura = fechamento anterior) em ``por_barra`` candles de 1m cuja agregação
    reproduz exatamente a barra: fechamentos interpolados, máxima no 2º minuto e mínima no 4º.
    ``maximas``/``minimas`` trocam a máxima/mínima de barras específicas (índice → preço)."""
    cb = np.asarray(c_barras, dtype="float64")
    ob = np.concatenate([[cb[0]], cb[:-1]])
    linhas_c, linhas_h, linhas_l, linhas_o = [], [], [], []
    maximas, minimas = maximas or {}, minimas or {}
    for b, (o, c) in enumerate(zip(ob, cb, strict=True)):
        fech = o + (c - o) * np.arange(1, por_barra + 1) / por_barra
        aber = np.concatenate([[o], fech[:-1]])
        h = np.maximum(aber, fech) + 0.01
        lo = np.minimum(aber, fech) - 0.01
        h[1 % por_barra] = maximas.get(b, max(o, c) + pavio)
        lo[3 % por_barra] = minimas.get(b, min(o, c) - pavio)
        linhas_c.append(fech)
        linhas_o.append(aber)
        linhas_h.append(h)
        linhas_l.append(lo)
    return minutos(
        np.concatenate(linhas_c),
        h=np.concatenate(linhas_h),
        lo=np.concatenate(linhas_l),
        o=np.concatenate(linhas_o),
        pressao=pressao,
        t0=t0,
    )


def anexar(
    df: pd.DataFrame, o: float, h: float, lo: float, c: float, p: float = 0.5
) -> pd.DataFrame:
    """Acrescenta um candle de 1m ao fim."""
    t = int(df.index[-1]) + M
    linha = pd.DataFrame(
        {"o": [o], "h": [h], "l": [lo], "c": [c], "v": [10.0], "vb": [10.0 * p]},
        index=pd.Index([t], name="abertura"),
    )
    return pd.concat([df, linha])
