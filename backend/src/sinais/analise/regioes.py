"""Regiões de suporte e resistência a partir de pivôs confirmados.

Cada pivô novo é fundido no nível mais próximo dentro de ``tolerancia_atr`` x ATR (um toque a
mais) ou vira um nível novo. Mais toques = região mais difícil de romper (limitado a
``toques_max`` para não crescer sem fim). Quando há níveis demais, sai o tocado há mais tempo.
Rompimentos usam os níveis conhecidos até o candle anterior. ``falso_rompimento`` +1: pavio
acima da resistência e fechamento de volta abaixo; -1: o mesmo no suporte.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from sinais.analise.estrutura import pivos
from sinais.analise.indicadores import atr


class Niveis:
    def __init__(self, maximo: int = 60, toques_max: int = 10) -> None:
        self._maximo = maximo
        self._toques_max = toques_max
        self._preco: list[float] = []
        self._toques: list[int] = []
        self._ultimo: list[int] = []

    def adicionar(self, preco: float, tolerancia: float, t: int) -> None:
        if self._preco:
            distancias = [abs(p - preco) for p in self._preco]
            j = int(np.argmin(distancias))
            if distancias[j] <= tolerancia:
                n = self._toques[j]
                self._preco[j] = (self._preco[j] * n + preco) / (n + 1)
                self._toques[j] = min(n + 1, self._toques_max)
                self._ultimo[j] = t
                return
        self._preco.append(preco)
        self._toques.append(1)
        self._ultimo.append(t)
        if len(self._preco) > self._maximo:
            j = int(np.argmin(self._ultimo))
            for lista in (self._preco, self._toques, self._ultimo):
                del lista[j]

    def niveis(self) -> list[tuple[float, int]]:
        return list(zip(self._preco, self._toques, strict=True))

    def vizinhos(self, c: float) -> tuple[tuple[float, int] | None, tuple[float, int] | None]:
        """(resistência logo acima de ``c``, suporte em ou logo abaixo de ``c``)."""
        res = sup = None
        for p, n in zip(self._preco, self._toques, strict=True):
            if p > c and (res is None or p < res[0]):
                res = (p, n)
            elif p <= c and (sup is None or p > sup[0]):
                sup = (p, n)
        return res, sup


def regioes(
    df: pd.DataFrame,
    k: int = 3,
    tolerancia_atr: float = 0.5,
    n_atr: int = 14,
    max_niveis: int = 60,
    toques_max: int = 10,
) -> pd.DataFrame:
    p = pivos(df, k)
    topos, fundos = p["topo"].to_numpy(), p["fundo"].to_numpy()
    a = atr(df, n_atr).to_numpy()
    h, lo, c = (df[x].to_numpy(dtype="float64") for x in ("h", "l", "c"))
    n = len(c)
    res_dist, sup_dist = np.full(n, np.nan), np.full(n, np.nan)
    res_toq, sup_toq = np.zeros(n, dtype="int64"), np.zeros(n, dtype="int64")
    romp, falso = np.zeros(n, dtype="int8"), np.zeros(n, dtype="int8")
    niveis = Niveis(max_niveis, toques_max)
    res_ant = sup_ant = np.nan
    for i in range(n):
        if i > 0:
            if res_ant == res_ant:
                if c[i - 1] <= res_ant < c[i]:
                    romp[i] = 1
                elif h[i] > res_ant >= c[i]:
                    falso[i] = 1
            if sup_ant == sup_ant:
                if c[i - 1] >= sup_ant > c[i]:
                    romp[i] = -1
                elif lo[i] < sup_ant <= c[i]:
                    falso[i] = -1
        tol = tolerancia_atr * a[i] if a[i] == a[i] else 0.0
        if topos[i] == topos[i]:
            niveis.adicionar(float(topos[i]), tol, i)
        if fundos[i] == fundos[i]:
            niveis.adicionar(float(fundos[i]), tol, i)
        res, sup = niveis.vizinhos(c[i])
        res_ant = res[0] if res else np.nan
        sup_ant = sup[0] if sup else np.nan
        if res:
            res_toq[i] = res[1]
            if a[i] > 0:
                res_dist[i] = (res[0] - c[i]) / a[i]
        if sup:
            sup_toq[i] = sup[1]
            if a[i] > 0:
                sup_dist[i] = (c[i] - sup[0]) / a[i]
    return pd.DataFrame(
        {
            "res_dist": res_dist,
            "sup_dist": sup_dist,
            "res_toques": res_toq,
            "sup_toques": sup_toq,
            "rompimento": romp,
            "falso_rompimento": falso,
        },
        index=df.index,
    )
