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


def rotular_1s(
    decisoes: np.ndarray,
    regra: RegraVencimento,
    precos_1s: SeriePrecos,
    latencia_ms: int = 2000,
    semente: int = 0,
    limiar_apertado: float = 1e-4,
) -> pd.DataFrame:
    """Rótulo realista (design §13.1): entrada num segundo inteiro sorteado entre
    ``teto(decisao + latencia)`` e o prazo de compra do vencimento mirado na decisão; preços de
    1 s. ``alvo`` como em ``rotular``; ``apertado`` = 1 se |vencimento − entrada| ≤
    ``limiar_apertado`` x entrada (mesma regra do simulador), NaN sem preço."""
    decisoes = np.asarray(decisoes, dtype="int64")
    venc = vencimentos(decisoes, regra)
    menor = -(-(decisoes + latencia_ms) // 1000)
    maior = (venc - regra.corte_ms - 1) // 1000
    rng = np.random.default_rng(semente)
    entrada = rng.integers(menor, np.maximum(maior, menor) + 1) * 1000
    pe = precos_1s.precos_em(entrada)
    pv = precos_1s.precos_em(venc)
    sem_preco = np.isnan(pe) | np.isnan(pv) | (maior < menor)
    alvo = np.where(pv > pe, 1.0, np.where(pv < pe, 0.0, np.nan))
    apertado = (np.abs(pv - pe) <= limiar_apertado * pe).astype("float64")
    alvo[sem_preco] = np.nan
    apertado[sem_preco] = np.nan
    return pd.DataFrame(
        {
            "decisao": decisoes,
            "entrada_t": entrada,
            "vencimento_t": venc,
            "alvo": alvo,
            "apertado": apertado,
        }
    )
