"""Análise de volume. Volume zero vira NaN (nunca divisão por zero)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from sinais.analise.indicadores import sma

_DIA_MS = 86_400_000


def _div(num: pd.Series, den: pd.Series) -> pd.Series:
    return num / den.where(den != 0)


def volume_relativo(df: pd.DataFrame, n: int = 20) -> pd.Series:
    return _div(df["v"], sma(df["v"], n))


def expansao_volume(df: pd.DataFrame, n: int = 20, curta: int = 5) -> pd.Series:
    """Média curta sobre média longa, menos 1: positivo = volume expandindo."""
    return _div(sma(df["v"], curta), sma(df["v"], n)) - 1


def pressao_acumulada(df: pd.DataFrame, n: int = 20) -> pd.Series:
    """(compra agressora - venda agressora) / volume, somados em ``n`` candles. De -1 a 1."""
    saldo = (2 * df["vb"] - df["v"]).rolling(n, min_periods=n).sum()
    return _div(saldo, df["v"].rolling(n, min_periods=n).sum())


def divergencia_volume(df: pd.DataFrame, n: int = 14) -> pd.Series:
    """-1: preço sobe com volume caindo (alta fraca). +1: preço cai com volume caindo."""
    preco = np.sign(df["c"] - df["c"].shift(n))
    media = sma(df["v"], n)
    volume = np.sign(media - media.shift(n))
    saida = pd.Series(0, index=df.index, dtype="int8")
    saida[(preco > 0) & (volume < 0)] = -1
    saida[(preco < 0) & (volume < 0)] = 1
    return saida


def vwap(df: pd.DataFrame, periodo_ms: int = _DIA_MS) -> pd.Series:
    """VWAP reiniciado a cada ``periodo_ms`` (padrão: dia UTC). Exige índice em ms."""
    sessao = pd.Series(df.index.to_numpy() // periodo_ms, index=df.index)
    tipico = (df["h"] + df["l"] + df["c"]) / 3
    pv = (tipico * df["v"]).groupby(sessao).cumsum()
    return _div(pv, df["v"].groupby(sessao).cumsum())
