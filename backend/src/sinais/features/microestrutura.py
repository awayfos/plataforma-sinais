"""Microestrutura a partir de klines de 1 s, agregada por minuto (parte do conjunto ``fs-2``).

``agregar_segundos`` resume os segundos de cada minuto ``t`` (aberturas em ``[t, t + 60 s)``)
em somas e marcos; ``features_microestrutura`` transforma o resumo em colunas ``mic_*``
estacionárias, com janelas que olham só para trás. O valor do minuto ``t`` usa apenas segundos
que fecham até o fim do minuto ``t`` (o instante de decisão).

Para séries longas, ``AgregadorMicro`` agrega mês a mês (cortes em fronteiras de minuto) e dá o
mesmo resultado da série inteira: guarda o último segundo do pedaço anterior, que é tudo o que
a variação do primeiro segundo do pedaço seguinte precisa.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

_MINUTO_MS = 60_000
_SEGUNDO_MS = 1000
# Segundo anterior só vale como referência de variação se estiver a até 5 s.
_MAX_SALTO_MS = 5 * _SEGUNDO_MS
# Minutos de agregados que o cálculo ao vivo precisa para reproduzir o histórico
# (janelas de 15 min e "segundos desde a mudança" com limite de 60 min).
JANELA_AO_VIVO_MICRO_MIN = 120
_LIMITE_MUDANCA_MIN = 60

COLUNAS_AGREGADO = [
    "n_seg",
    "v",
    "vb",
    "n",
    "v_ult10",
    "vb_ult10",
    "c_fim",
    "c_s49",
    "c_s29",
    "soma_r2",
    "seg_parados",
    "t_ult_mudanca",
    "seq_fim",
    "vwap",
]


def agregar_segundos(df_1s: pd.DataFrame) -> pd.DataFrame:
    """Resumo por minuto. Espera colunas ``c, v, vb, n`` e índice = abertura do segundo (ms)."""
    t = df_1s.index.to_numpy(dtype="int64")
    c = df_1s["c"].to_numpy(dtype="float64")
    v = df_1s["v"].to_numpy(dtype="float64")
    vb = df_1s["vb"].to_numpy(dtype="float64")
    minuto = t - t % _MINUTO_MS
    s = (t % _MINUTO_MS) // _SEGUNDO_MS
    r = np.full(len(c), np.nan)
    if len(c) > 1:
        valido = (t[1:] - t[:-1]) <= _MAX_SALTO_MS
        r[1:] = np.where(valido, np.log(c[1:] / c[:-1]), np.nan)
    mudou = ~np.isnan(r) & (r != 0)
    ult10 = s >= 50
    quadro = pd.DataFrame(
        {
            "minuto": minuto,
            "um": 1.0,
            "v": v,
            "vb": vb,
            "n": df_1s["n"].to_numpy(dtype="float64"),
            "v_ult10": np.where(ult10, v, 0.0),
            "vb_ult10": np.where(ult10, vb, 0.0),
            "c_fim": c,
            "c_s49": np.where(s <= 49, c, np.nan),
            "c_s29": np.where(s <= 29, c, np.nan),
            "r2": r * r,
            "parado": (r == 0).astype("float64"),
            "t_mud": np.where(mudou, t, np.nan),
            "cv": c * v,
        }
    )
    g = quadro.groupby("minuto", sort=True)
    somas = g[["um", "v", "vb", "n", "v_ult10", "vb_ult10", "parado", "cv"]].sum()
    ultimos = g[["c_fim", "c_s49", "c_s29"]].last()  # last() ignora NaN
    saida = pd.DataFrame(
        {
            "n_seg": somas["um"],
            "v": somas["v"],
            "vb": somas["vb"],
            "n": somas["n"],
            "v_ult10": somas["v_ult10"],
            "vb_ult10": somas["vb_ult10"],
            "c_fim": ultimos["c_fim"],
            "c_s49": ultimos["c_s49"],
            "c_s29": ultimos["c_s29"],
            "soma_r2": g["r2"].sum(min_count=1),
            "seg_parados": somas["parado"],
            "t_ult_mudanca": g["t_mud"].max(),
            "seq_fim": _sequencia_final(minuto, r, mudou).reindex(somas.index, fill_value=0.0),
            "vwap": somas["cv"] / somas["v"].where(somas["v"] > 0),
        }
    )
    saida.index = pd.Index(saida.index.to_numpy(dtype="int64"), name="abertura")
    return saida.astype("float64")


def _sequencia_final(minuto: np.ndarray, r: np.ndarray, mudou: np.ndarray) -> pd.Series:
    """Por minuto: tamanho da última sequência de segundos com variação no mesmo sentido
    (segundos parados não quebram nem contam), com o sinal do sentido."""
    m = minuto[mudou]
    d = np.sign(r[mudou])
    if not len(d):
        return pd.Series(dtype="float64")
    novo = np.r_[True, (d[1:] != d[:-1]) | (m[1:] != m[:-1])]
    rodada = np.cumsum(novo)
    pos = pd.Series(np.ones(len(d))).groupby(rodada).cumsum().to_numpy()
    return pd.Series(d * pos).groupby(m).last()


class AgregadorMicro:
    """Agrega pedaços consecutivos (cortados em fronteira de minuto) sem perder a variação do
    primeiro segundo de cada pedaço."""

    def __init__(self) -> None:
        self._partes: list[pd.DataFrame] = []
        self._cauda: pd.DataFrame | None = None

    def adicionar(self, df_1s: pd.DataFrame) -> None:
        if df_1s.empty:
            return
        inicio = int(df_1s.index[0])
        estendido = df_1s if self._cauda is None else pd.concat([self._cauda, df_1s])
        agg = agregar_segundos(estendido)
        self._partes.append(agg[agg.index >= inicio - inicio % _MINUTO_MS])
        self._cauda = df_1s.iloc[-1:]

    def resultado(self) -> pd.DataFrame:
        if not self._partes:
            return pd.DataFrame(columns=COLUNAS_AGREGADO, dtype="float64")
        return pd.concat(self._partes)


def _razao(a: pd.Series, b: pd.Series) -> pd.Series:
    return a / b.where(b > 0)


def features_microestrutura(agg: pd.DataFrame) -> pd.DataFrame:
    """Colunas ``mic_*`` por minuto. Janelas posicionais, só para trás."""
    vol = np.sqrt(agg["soma_r2"])
    v_med15 = agg["v"].rolling(15, min_periods=5).mean()
    fim = agg.index.to_numpy(dtype="int64") + _MINUTO_MS
    ult_mud = agg["t_ult_mudanca"].ffill(limit=_LIMITE_MUDANCA_MIN)
    frac_parados = _razao(agg["seg_parados"], agg["n_seg"])
    compra_ini = _razao(agg["vb"] - agg["vb_ult10"], agg["v"] - agg["v_ult10"])
    compra_ult10 = _razao(agg["vb_ult10"], agg["v_ult10"])
    colunas = {
        "mic_compra_min": _razao(agg["vb"], agg["v"]),
        "mic_compra_ult10": compra_ult10,
        "mic_compra_delta": compra_ult10 - compra_ini,
        "mic_ret_ult10": _razao(np.log(agg["c_fim"] / agg["c_s49"]), vol),
        "mic_ret_ult30": _razao(np.log(agg["c_fim"] / agg["c_s29"]), vol),
        "mic_vol_real_bps": vol * 1e4,
        "mic_vol_real_5m_bps": np.sqrt(agg["soma_r2"].rolling(5, min_periods=5).sum()) * 1e4,
        "mic_vol_real_rel15": _razao(vol, vol.rolling(15, min_periods=5).mean()),
        "mic_frac_parados": frac_parados,
        "mic_frac_parados_15": frac_parados.rolling(15, min_periods=5).mean(),
        "mic_seg_desde_mudanca": (fim - (ult_mud + _SEGUNDO_MS)) / _SEGUNDO_MS,
        "mic_explosao_10s": _razao(agg["v_ult10"] / 10, _razao(agg["v"], agg["n_seg"])),
        "mic_explosao_10s_vs15": _razao(agg["v_ult10"] / 10, v_med15 / 60),
        "mic_sequencia": agg["seq_fim"],
        "mic_trades_rel15": _razao(agg["n"], agg["n"].rolling(15, min_periods=5).mean()),
        "mic_vwap_dist": _razao(np.log(agg["c_fim"] / agg["vwap"]), vol),
        "mic_seg_presentes": agg["n_seg"],
    }
    saida = pd.DataFrame(colunas, index=agg.index).astype("float64")
    return saida.replace([np.inf, -np.inf], np.nan)
