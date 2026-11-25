"""Rótulos de direção para cada decisão no fechamento do minuto."""

from __future__ import annotations

import numpy as np
import pandas as pd

from sinais.backtest.precos import SeriePrecos
from sinais.corretoras.regras import RegraVencimento

_MINUTO_MS = 60_000


def vencimentos(decisoes: np.ndarray, regra: RegraVencimento) -> np.ndarray:
    """Vetorização de ``RegraVencimento.vencimento_para``."""
    proximo = decisoes - decisoes % regra.grade_ms + regra.grade_ms
    return np.asarray(
        np.where(proximo - decisoes > regra.corte_ms, proximo, proximo + regra.grade_ms)
    )


def rotular(df_1m: pd.DataFrame, regra: RegraVencimento, precos: SeriePrecos) -> pd.DataFrame:
    """``alvo`` = 1 se o preço no vencimento supera o de entrada, 0 se fica abaixo,
    NaN em empate ou sem preço (ex.: vencimento depois do fim dos dados)."""
    decisao = df_1m.index.to_numpy(dtype="int64") + _MINUTO_MS
    venc = vencimentos(decisao, regra)
    entrada = precos.precos_em(decisao)
    final = precos.precos_em(venc)
    alvo = np.where(final > entrada, 1.0, np.where(final < entrada, 0.0, np.nan))
    alvo[np.isnan(entrada) | np.isnan(final)] = np.nan
    return pd.DataFrame({"decisao": decisao, "vencimento_t": venc, "alvo": alvo}, index=df_1m.index)
