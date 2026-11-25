"""Pivôs e estrutura de mercado (HH/HL/LH/LL, BOS, CHoCH).

Um pivô no candle ``i`` só é conhecido em ``i + k``, quando os ``k`` candles à direita o
confirmam. Por isso todas as saídas aparecem na linha de confirmação: nada usa o futuro.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def pivos(df: pd.DataFrame, k: int = 3) -> pd.DataFrame:
    h, lo = df["h"].to_numpy(dtype="float64"), df["l"].to_numpy(dtype="float64")
    n = len(h)
    topo, fundo = np.full(n, np.nan), np.full(n, np.nan)
    for i in range(k, n - k):
        if h[i] > h[i - k : i].max() and h[i] >= h[i + 1 : i + k + 1].max():
            topo[i + k] = h[i]
        if lo[i] < lo[i - k : i].min() and lo[i] <= lo[i + 1 : i + k + 1].min():
            fundo[i + k] = lo[i]
    return pd.DataFrame({"topo": topo, "fundo": fundo, "idade": k}, index=df.index)


def estrutura(df: pd.DataFrame, k: int = 3) -> pd.DataFrame:
    p = pivos(df, k)
    topos, fundos = p["topo"].to_numpy(), p["fundo"].to_numpy()
    c = df["c"].to_numpy(dtype="float64")
    n = len(c)
    cols = {
        nome: np.zeros(n, dtype="int8")
        for nome in ("rotulo_topo", "rotulo_fundo", "tendencia", "bos", "choch")
    }
    ultimo_topo, ultimo_fundo = np.full(n, np.nan), np.full(n, np.nan)
    topo = fundo = float("nan")
    rot_t = rot_f = 0
    for i in range(n):
        novo_t, novo_f = topos[i], fundos[i]
        if not np.isnan(novo_t):
            rot_t = 0 if np.isnan(topo) else (1 if novo_t > topo else -1)
            topo = novo_t
        if not np.isnan(novo_f):
            rot_f = 0 if np.isnan(fundo) else (1 if novo_f > fundo else -1)
            fundo = novo_f
        tendencia = 1 if rot_t == rot_f == 1 else (-1 if rot_t == rot_f == -1 else 0)
        cols["rotulo_topo"][i], cols["rotulo_fundo"][i] = rot_t, rot_f
        cols["tendencia"][i] = tendencia
        ultimo_topo[i], ultimo_fundo[i] = topo, fundo
        if i == 0:
            continue
        rompe_cima = not np.isnan(topo) and c[i - 1] <= topo < c[i]
        rompe_baixo = not np.isnan(fundo) and c[i - 1] >= fundo > c[i]
        if rompe_cima:
            cols["choch" if tendencia == -1 else "bos"][i] = 1
        if rompe_baixo:
            cols["choch" if tendencia == 1 else "bos"][i] = -1
    saida = pd.DataFrame(cols, index=df.index)
    saida["ultimo_topo"], saida["ultimo_fundo"] = ultimo_topo, ultimo_fundo
    return saida
