"""Padrões de candle e força do candle. Usam só o candle atual e os anteriores.

Direcionais devolvem ``int8`` (1 alta, -1 baixa, 0 nada); os demais, ``bool``.
Candle com amplitude zero nunca forma padrão.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _partes(df: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    corpo = (df["c"] - df["o"]).abs()
    amp = df["h"] - df["l"]
    sup = df["h"] - df[["o", "c"]].max(axis=1)
    inf = df[["o", "c"]].min(axis=1) - df["l"]
    return corpo, amp, sup, inf


def _dir(alta: pd.Series, baixa: pd.Series) -> pd.Series:
    return (alta.astype("int8") - baixa.astype("int8")).astype("int8")


def doji(df: pd.DataFrame, corpo_max: float = 0.1) -> pd.Series:
    corpo, amp, _, _ = _partes(df)
    return (amp > 0) & (corpo <= corpo_max * amp)


def martelo(df: pd.DataFrame, pavio_oposto_max: float = 0.1) -> pd.Series:
    corpo, amp, sup, inf = _partes(df)
    return (amp > 0) & (inf >= 2 * corpo) & (sup <= pavio_oposto_max * amp) & (inf > 0)


def estrela_cadente(df: pd.DataFrame, pavio_oposto_max: float = 0.1) -> pd.Series:
    corpo, amp, sup, inf = _partes(df)
    return (amp > 0) & (sup >= 2 * corpo) & (inf <= pavio_oposto_max * amp) & (sup > 0)


def pin_bar(df: pd.DataFrame, pavio_min: float = 2 / 3) -> pd.Series:
    _, amp, sup, inf = _partes(df)
    amp_ok = amp.where(amp > 0)
    return _dir((inf / amp_ok) >= pavio_min, (sup / amp_ok) >= pavio_min)


def engolfo(df: pd.DataFrame) -> pd.Series:
    o1, c1 = df["o"].shift(1), df["c"].shift(1)
    corpo, corpo1 = (df["c"] - df["o"]).abs(), (c1 - o1).abs()
    alta = (c1 < o1) & (df["c"] > df["o"]) & (df["o"] <= c1) & (df["c"] >= o1) & (corpo > corpo1)
    baixa = (c1 > o1) & (df["c"] < df["o"]) & (df["o"] >= c1) & (df["c"] <= o1) & (corpo > corpo1)
    return _dir(alta, baixa)


def marubozu(df: pd.DataFrame, pavio_max: float = 0.05) -> pd.Series:
    corpo, amp, sup, inf = _partes(df)
    cheio = (amp > 0) & (corpo > 0) & ((sup + inf) <= pavio_max * amp)
    return _dir(cheio & (df["c"] > df["o"]), cheio & (df["c"] < df["o"]))


def inside_bar(df: pd.DataFrame) -> pd.Series:
    return (df["h"] < df["h"].shift(1)) & (df["l"] > df["l"].shift(1))


def outside_bar(df: pd.DataFrame) -> pd.Series:
    return (df["h"] > df["h"].shift(1)) & (df["l"] < df["l"].shift(1))


def _estrela(df: pd.DataFrame, alta: bool) -> pd.Series:
    corpo, amp, _, _ = _partes(df)
    o2, c2 = df["o"].shift(2), df["c"].shift(2)
    grande = corpo.shift(2) >= 0.6 * amp.shift(2)
    pequeno = corpo.shift(1) <= 0.3 * corpo.shift(2)
    meio = (o2 + c2) / 2
    if alta:
        return (c2 < o2) & grande & pequeno & (df["c"] > df["o"]) & (df["c"] > meio)
    return (c2 > o2) & grande & pequeno & (df["c"] < df["o"]) & (df["c"] < meio)


def estrela_manha(df: pd.DataFrame) -> pd.Series:
    return _estrela(df, alta=True)


def estrela_tarde(df: pd.DataFrame) -> pd.Series:
    return _estrela(df, alta=False)


def sequencia(df: pd.DataFrame) -> pd.Series:
    """Quantos candles seguidos na mesma direção, com sinal (doji zera)."""
    direcao = np.sign((df["c"] - df["o"]).to_numpy())
    saida = np.zeros(len(direcao), dtype="int64")
    for i, d in enumerate(direcao):
        if d == 0:
            continue
        anterior = saida[i - 1] if i else 0
        saida[i] = anterior + int(d) if np.sign(anterior) == d else int(d)
    return pd.Series(saida, index=df.index)


def forca(df: pd.DataFrame) -> pd.DataFrame:
    amp = (df["h"] - df["l"]).where(lambda a: a > 0)
    v = df["v"].where(df["v"] > 0)
    return pd.DataFrame(
        {"corpo_rel": (df["c"] - df["o"]) / amp, "pressao_compradora": df["vb"] / v - 0.5}
    )
