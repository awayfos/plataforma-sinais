"""Price action: inclinação, impulso, desaceleração, lateralização, rejeição, correção e
continuidade. Medidas em unidades de ATR para serem comparáveis entre ativos."""

from __future__ import annotations

import numpy as np
import pandas as pd

from sinais.analise.estrutura import estrutura
from sinais.analise.indicadores import adx, atr, bollinger, ema


def price_action(
    df: pd.DataFrame, n: int = 14, k: int = 3, est: pd.DataFrame | None = None
) -> pd.DataFrame:
    a = atr(df, n)
    a = a.where(a > 0)
    media = ema(df["c"], 20)
    inclinacao = (media - media.shift(1)) / a
    impulso = (df["c"] - df["c"].shift(n)).abs() / a
    largura = bollinger(df["c"], 20)["largura"]
    mediana = largura.rolling(500, min_periods=100).median()
    lateral = (adx(df, n)["adx"] < 20) & (largura < mediana)
    amp = (df["h"] - df["l"]).where(lambda x: x > 0)
    sup = df["h"] - df[["o", "c"]].max(axis=1)
    inf = df[["o", "c"]].min(axis=1) - df["l"]
    e = estrutura(df, k) if est is None else est
    correcao = pd.Series(np.nan, index=df.index)
    correcao[e["tendencia"] == 1] = (e["ultimo_topo"] - df["c"]) / a
    correcao[e["tendencia"] == -1] = (df["c"] - e["ultimo_fundo"]) / a
    mesma = (np.sign(df["c"] - df["o"]) == np.sign(inclinacao)).astype("float64")
    continuidade = mesma.where(inclinacao.notna()).rolling(n, min_periods=n).mean()
    return pd.DataFrame(
        {
            "inclinacao_ema": inclinacao,
            "impulso": impulso,
            "desaceleracao": impulso - impulso.shift(n // 2),
            "lateral": lateral,
            "rejeicao": (sup - inf) / amp,
            "correcao": correcao,
            "continuidade": continuidade,
        },
        index=df.index,
    )
