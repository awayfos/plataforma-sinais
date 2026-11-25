"""Estratégias simples de comparação. Qualquer modelo precisa superá-las fora da amostra.

Todas decidem no fechamento de cada minuto (``abertura + 60 s``) e devolvem ``decisao``
(ms) e ``direcao`` (+1 compra, -1 venda).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

_MINUTO_MS = 60_000


def _sinais(df: pd.DataFrame, direcao: np.ndarray) -> pd.DataFrame:
    decisao = df.index.to_numpy(dtype="int64") + _MINUTO_MS
    mascara = direcao != 0
    return pd.DataFrame(
        {"decisao": decisao[mascara], "direcao": direcao[mascara].astype("int64")}
    ).reset_index(drop=True)


def sempre_compra(df: pd.DataFrame) -> pd.DataFrame:
    return _sinais(df, np.ones(len(df), dtype="int64"))


def sempre_venda(df: pd.DataFrame) -> pd.DataFrame:
    return _sinais(df, -np.ones(len(df), dtype="int64"))


def seguir_ultimo(df: pd.DataFrame) -> pd.DataFrame:
    """Aposta que o próximo candle repete a direção do último (doji não sinaliza)."""
    return _sinais(df, np.sign(df["c"].to_numpy() - df["o"].to_numpy()).astype("int64"))


def aleatoria(df: pd.DataFrame, semente: int = 0, prob: float = 1.0) -> pd.DataFrame:
    rng = np.random.default_rng(semente)
    direcao = rng.choice([-1, 1], size=len(df))
    direcao[rng.random(len(df)) >= prob] = 0
    return _sinais(df, direcao)
