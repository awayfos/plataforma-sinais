"""Métricas honestas: taxa sem empates, intervalo de Wilson, ponto de equilíbrio do payout,
valor esperado por operação, p-valor binomial exato e correção de Benjamini-Hochberg."""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import pandas as pd
from scipy.stats import binom

from sinais.corretoras.regras import ponto_equilibrio

Z95 = 1.959964


def wilson(acertos: int, n: int, z: float = Z95) -> tuple[float, float]:
    if n == 0:
        return math.nan, math.nan
    p = acertos / n
    den = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / den
    margem = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return centro - margem, centro + margem


@dataclass(frozen=True)
class Metricas:
    n: int  # operações liquidadas (WIN + LOSS + TIE)
    wins: int
    losses: int
    ties: int
    fora_janela: int
    sem_dado: int
    taxa: float  # wins / (wins + losses)
    wilson_inf: float
    wilson_sup: float
    p_equilibrio: float
    valor_esperado: float  # por operação liquidada, em unidades do valor investido
    pvalor: float


def pvalor_acima_equilibrio(acertos: int, n: int, p_eq: float) -> float:
    """P(X >= acertos) com X ~ Binomial(n, p_eq): chance de acertar tanto só por sorte."""
    if n == 0:
        return math.nan
    return float(binom.sf(acertos - 1, n, p_eq))


def calcular(operacoes: pd.DataFrame, payout: float) -> Metricas:
    r = operacoes["resultado"].value_counts() if len(operacoes) else pd.Series(dtype="int64")
    wins, losses, ties = (int(r.get(k, 0)) for k in ("WIN", "LOSS", "TIE"))
    decididas = wins + losses
    n = decididas + ties
    p_eq = ponto_equilibrio(payout)
    inf, sup = wilson(wins, decididas)
    return Metricas(
        n=n,
        wins=wins,
        losses=losses,
        ties=ties,
        fora_janela=int(r.get("FORA_DA_JANELA", 0)),
        sem_dado=int(r.get("SEM_DADO", 0)),
        taxa=wins / decididas if decididas else math.nan,
        wilson_inf=inf,
        wilson_sup=sup,
        p_equilibrio=p_eq,
        valor_esperado=(wins * payout - losses) / n if n else math.nan,
        pvalor=pvalor_acima_equilibrio(wins, decididas, p_eq),
    )


def por_grupo(
    operacoes: pd.DataFrame,
    payout: float,
    chave: Callable[[pd.DataFrame], pd.Series],
) -> dict[str, Metricas]:
    grupos = chave(operacoes)
    return {str(g): calcular(operacoes[grupos == g], payout) for g in sorted(grupos.unique())}


def benjamini_hochberg(pvalores: Sequence[float], q: float = 0.05) -> list[bool]:
    """Quais hipóteses rejeitar controlando a taxa de falsas descobertas em ``q``."""
    m = len(pvalores)
    ordem = sorted(range(m), key=lambda i: pvalores[i])
    limite = -1
    for posicao, i in enumerate(ordem, start=1):
        if pvalores[i] <= q * posicao / m:
            limite = posicao
    aprovados = set(ordem[:limite]) if limite > 0 else set()
    return [i in aprovados for i in range(m)]
