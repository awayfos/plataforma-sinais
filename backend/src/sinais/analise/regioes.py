"""Regiões de suporte e resistência a partir de pivôs confirmados.

Pivôs próximos (dentro de ``tolerancia_atr`` x ATR) formam um mesmo nível; cada pivô agrupado
é um toque. Mais toques = região mais difícil de romper. Rompimentos usam os níveis conhecidos
até o candle anterior. ``falso_rompimento`` +1: pavio acima da resistência e fechamento de volta
abaixo; -1: o mesmo no suporte.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from sinais.analise.estrutura import pivos
from sinais.analise.indicadores import atr

_MAX_NIVEIS = 60


def regioes(
    df: pd.DataFrame, k: int = 3, tolerancia_atr: float = 0.5, n_atr: int = 14
) -> pd.DataFrame:
    p = pivos(df, k)
    a = atr(df, n_atr).to_numpy()
    h, lo, c = (df[x].to_numpy(dtype="float64") for x in ("h", "l", "c"))
    n = len(c)
    saida = {
        "res_dist": np.full(n, np.nan),
        "sup_dist": np.full(n, np.nan),
        "res_toques": np.zeros(n, dtype="int64"),
        "sup_toques": np.zeros(n, dtype="int64"),
        "rompimento": np.zeros(n, dtype="int8"),
        "falso_rompimento": np.zeros(n, dtype="int8"),
    }
    niveis: list[list[float]] = []  # [preço, toques]
    res_ant = sup_ant = float("nan")

    for i in range(n):
        if i > 0:
            if not np.isnan(res_ant):
                if c[i - 1] <= res_ant < c[i]:
                    saida["rompimento"][i] = 1
                elif h[i] > res_ant >= c[i]:
                    saida["falso_rompimento"][i] = 1
            if not np.isnan(sup_ant):
                if c[i - 1] >= sup_ant > c[i]:
                    saida["rompimento"][i] = -1
                elif lo[i] < sup_ant <= c[i]:
                    saida["falso_rompimento"][i] = -1
        tol = tolerancia_atr * a[i] if not np.isnan(a[i]) else 0.0
        for preco in (p["topo"].iat[i], p["fundo"].iat[i]):
            if np.isnan(preco):
                continue
            perto = [nv for nv in niveis if abs(nv[0] - preco) <= tol]
            if perto:
                nv = perto[0]
                nv[0] = (nv[0] * nv[1] + preco) / (nv[1] + 1)
                nv[1] += 1
            else:
                niveis.append([preco, 1.0])
                del niveis[:-_MAX_NIVEIS]
        acima = [nv for nv in niveis if nv[0] > c[i]]
        abaixo = [nv for nv in niveis if nv[0] <= c[i]]
        res = min(acima, key=lambda nv: nv[0]) if acima else None
        sup = max(abaixo, key=lambda nv: nv[0]) if abaixo else None
        res_ant = res[0] if res else float("nan")
        sup_ant = sup[0] if sup else float("nan")
        if res:
            saida["res_toques"][i] = int(res[1])
            if a[i] > 0:
                saida["res_dist"][i] = (res[0] - c[i]) / a[i]
        if sup:
            saida["sup_toques"][i] = int(sup[1])
            if a[i] > 0:
                saida["sup_dist"][i] = (c[i] - sup[0]) / a[i]
    return pd.DataFrame(saida, index=df.index)
