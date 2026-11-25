"""Níveis de retração de Fibonacci e posição do preço no último movimento confirmado."""

from __future__ import annotations

import pandas as pd

from sinais.analise.estrutura import estrutura

PROPORCOES = {
    "0": 0.0,
    "23.6": 0.236,
    "38.2": 0.382,
    "50": 0.5,
    "61.8": 0.618,
    "78.6": 0.786,
    "100": 1.0,
}


def niveis_fibonacci(topo: float, fundo: float) -> dict[str, float]:
    """Retração a partir do topo: 0% = topo, 100% = fundo."""
    return {nome: topo - (topo - fundo) * p for nome, p in PROPORCOES.items()}


def posicao_fibonacci(df: pd.DataFrame, k: int = 3, est: pd.DataFrame | None = None) -> pd.Series:
    """0 = no último fundo confirmado, 1 = no último topo confirmado (pode passar dos limites)."""
    e = estrutura(df, k) if est is None else est
    faixa = e["ultimo_topo"] - e["ultimo_fundo"]
    return (df["c"] - e["ultimo_fundo"]) / faixa.where(faixa != 0)
