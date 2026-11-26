"""Base de cálculo por ativo: arrays de 1m e quadros fechados de 5m e 15m.

Para cada linha de 1m (decisão no fechamento, ``abertura + 60 s``), ``idx5``/``idx15`` apontam para
o último bloco **completo e já fechado** até a decisão; −1 se não houver ou se o bloco tiver idade
de uma duração ou mais (lacuna nos dados), como em ``features.snapshot.montar_snapshot``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from sinais.analise.indicadores import atr
from sinais.analise.volume import volume_relativo
from sinais.core.dominio import TempoGrafico
from sinais.features.snapshot import agregar_quadro
from sinais.situacoes.parametros import MINUTO_MS, N_ATR


@dataclass(frozen=True)
class Quadro:
    df: pd.DataFrame
    t: np.ndarray
    fech: np.ndarray
    h: np.ndarray
    l: np.ndarray  # noqa: E741
    c: np.ndarray
    atr: np.ndarray


@dataclass(frozen=True)
class Base:
    df: pd.DataFrame
    t: np.ndarray
    decisao: np.ndarray
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray  # noqa: E741
    c: np.ndarray
    v: np.ndarray
    vb: np.ndarray
    pressao: np.ndarray
    atr1: np.ndarray
    vol_rel: np.ndarray
    q5: Quadro
    q15: Quadro
    idx5: np.ndarray
    idx15: np.ndarray


def _quadro(df: pd.DataFrame, duracao_ms: int) -> Quadro:
    t = df.index.to_numpy(dtype="int64")
    return Quadro(
        df=df,
        t=t,
        fech=t + duracao_ms,
        h=df["h"].to_numpy(dtype="float64"),
        l=df["l"].to_numpy(dtype="float64"),
        c=df["c"].to_numpy(dtype="float64"),
        atr=atr(df, N_ATR).to_numpy(dtype="float64") if len(df) else np.zeros(0),
    )


def _mapa(decisao: np.ndarray, q: Quadro, duracao_ms: int) -> np.ndarray:
    j = np.searchsorted(q.fech, decisao, side="right") - 1
    ok = j >= 0
    idade = np.where(ok, decisao - q.fech[np.clip(j, 0, None)], 0) if len(q.fech) else 0
    return np.where(ok & (idade < duracao_ms), j, -1).astype("int64")


def montar_base(df_1m: pd.DataFrame) -> Base:
    t = df_1m.index.to_numpy(dtype="int64")
    decisao = t + MINUTO_MS
    v = df_1m["v"].to_numpy(dtype="float64")
    vb = df_1m["vb"].to_numpy(dtype="float64")
    with np.errstate(invalid="ignore", divide="ignore"):
        pressao = np.where(v > 0, vb / np.where(v > 0, v, 1.0), np.nan)
    quadros = {}
    mapas = {}
    for tg in (TempoGrafico.M5, TempoGrafico.M15):
        q = _quadro(agregar_quadro(df_1m, tg), tg.duracao_ms)
        quadros[tg] = q
        mapas[tg] = _mapa(decisao, q, tg.duracao_ms)
    return Base(
        df=df_1m,
        t=t,
        decisao=decisao,
        o=df_1m["o"].to_numpy(dtype="float64"),
        h=df_1m["h"].to_numpy(dtype="float64"),
        l=df_1m["l"].to_numpy(dtype="float64"),
        c=df_1m["c"].to_numpy(dtype="float64"),
        v=v,
        vb=vb,
        pressao=pressao,
        atr1=atr(df_1m, N_ATR).to_numpy(dtype="float64"),
        vol_rel=volume_relativo(df_1m, 20).to_numpy(dtype="float64"),
        q5=quadros[TempoGrafico.M5],
        q15=quadros[TempoGrafico.M15],
        idx5=mapas[TempoGrafico.M5],
        idx15=mapas[TempoGrafico.M15],
    )
