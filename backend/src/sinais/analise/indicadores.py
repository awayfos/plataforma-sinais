"""Indicadores técnicos causais. Aquecimento = NaN. Parâmetros configuráveis.

Médias de Wilder (RSI, ATR, ADX) usam RMA (alpha = 1/n) e EMA usa alpha = 2/(n+1); as duas são
semeadas pela média simples dos primeiros ``n`` valores válidos, como no TA-Lib.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _media_semeada(s: pd.Series, n: int, alpha: float) -> pd.Series:
    x = s.to_numpy(dtype="float64")
    saida = np.full(len(x), np.nan)
    validos = np.flatnonzero(~np.isnan(x))
    if len(validos) < n:
        return pd.Series(saida, index=s.index)
    inicio = validos[0]
    semente = inicio + n - 1
    if np.isnan(x[inicio : semente + 1]).any():
        return pd.Series(saida, index=s.index)
    anterior = float(x[inicio : semente + 1].mean())
    saida[semente] = anterior
    for i in range(semente + 1, len(x)):
        if not np.isnan(x[i]):
            anterior = anterior + alpha * (x[i] - anterior)
        saida[i] = anterior
    return pd.Series(saida, index=s.index)


def sma(s: pd.Series, n: int = 20) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()


def ema(s: pd.Series, n: int = 20) -> pd.Series:
    return _media_semeada(s, n, 2.0 / (n + 1))


def rma(s: pd.Series, n: int = 14) -> pd.Series:
    return _media_semeada(s, n, 1.0 / n)


def _razao(num: pd.Series, den: pd.Series, vazio: float) -> pd.Series:
    """num/den; onde den == 0 devolve ``vazio`` (preserva NaN de aquecimento)."""
    r = num / den.where(den != 0)
    return r.where(~((den == 0) & num.notna()), vazio)


def rsi(c: pd.Series, n: int = 14) -> pd.Series:
    delta = c.diff()
    ganho = rma(delta.clip(lower=0), n)
    perda = rma((-delta).clip(lower=0), n)
    total = ganho + perda
    return 100 * _razao(ganho, total, 0.5)


def macd(c: pd.Series, rapida: int = 12, lenta: int = 26, sinal: int = 9) -> pd.DataFrame:
    linha = ema(c, rapida) - ema(c, lenta)
    s = ema(linha, sinal)
    return pd.DataFrame({"macd": linha, "sinal": s, "hist": linha - s})


def bollinger(c: pd.Series, n: int = 20, k: float = 2.0) -> pd.DataFrame:
    media = sma(c, n)
    desvio = c.rolling(n, min_periods=n).std(ddof=0)
    sup, inf = media + k * desvio, media - k * desvio
    return pd.DataFrame(
        {"media": media, "sup": sup, "inf": inf, "largura": _razao(sup - inf, media, 0.0)}
    )


def true_range(df: pd.DataFrame) -> pd.Series:
    anterior = df["c"].shift(1)
    faixas = pd.concat(
        [df["h"] - df["l"], (df["h"] - anterior).abs(), (df["l"] - anterior).abs()], axis=1
    )
    return faixas.max(axis=1)


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    return rma(true_range(df), n)


def adx(df: pd.DataFrame, n: int = 14) -> pd.DataFrame:
    sobe = df["h"].diff()
    desce = -df["l"].diff()
    mais_dm = sobe.where((sobe > desce) & (sobe > 0), 0.0).where(sobe.notna())
    menos_dm = desce.where((desce > sobe) & (desce > 0), 0.0).where(desce.notna())
    tr = true_range(df).where(sobe.notna())
    tr_s = rma(tr, n)
    mais_di = 100 * _razao(rma(mais_dm, n), tr_s, 0.0)
    menos_di = 100 * _razao(rma(menos_dm, n), tr_s, 0.0)
    dx = 100 * _razao((mais_di - menos_di).abs(), mais_di + menos_di, 0.0)
    return pd.DataFrame({"adx": rma(dx, n), "mais_di": mais_di, "menos_di": menos_di})


def estocastico(df: pd.DataFrame, n: int = 14, suav_k: int = 3, d: int = 3) -> pd.DataFrame:
    minima = df["l"].rolling(n, min_periods=n).min()
    maxima = df["h"].rolling(n, min_periods=n).max()
    bruto = 100 * _razao(df["c"] - minima, maxima - minima, 0.5)
    k = sma(bruto, suav_k)
    return pd.DataFrame({"k": k, "d": sma(k, d)})


def _meio(df: pd.DataFrame, n: int) -> pd.Series:
    return (df["h"].rolling(n, min_periods=n).max() + df["l"].rolling(n, min_periods=n).min()) / 2


def ichimoku(df: pd.DataFrame, tenkan: int = 9, kijun: int = 26, senkou: int = 52) -> pd.DataFrame:
    """Spans deslocadas ``kijun`` candles para frente: o valor em ``t`` vem de ``t - kijun``."""
    t, k = _meio(df, tenkan), _meio(df, kijun)
    return pd.DataFrame(
        {
            "tenkan": t,
            "kijun": k,
            "span_a": ((t + k) / 2).shift(kijun),
            "span_b": _meio(df, senkou).shift(kijun),
        }
    )


def chikou(df: pd.DataFrame, deslocamento: int = 26) -> pd.Series:
    """Só para o gráfico: usa preços futuros e por isso nunca entra nas features."""
    return df["c"].shift(-deslocamento)
