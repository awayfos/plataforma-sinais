"""Filtro de operações apertadas (AGUARDAR quando o preço tende a quase não mexer).

Um classificador prevê, no instante da decisão, a chance de a operação terminar "apertada"
(|vencimento − entrada| ≤ 0,01% do preço). Nessas operações o resultado é quase moeda e o preço
da corretora pode divergir da referência. O limiar é escolhido **só na calibração**: entre não
filtrar e cortar os 10%, 25% ou 50% de maior ``p_apertado``, fica o de maior limite inferior de
Wilson da taxa de acerto das decisões que passam; empate fica com o menos restritivo.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from sinais.backtest.metricas import wilson
from sinais.modelos.treino import HIPERPARAMETROS, ErroTreino


@dataclass
class FiltroApertado:
    estimador: Any

    def probabilidade(self, x: np.ndarray) -> np.ndarray:
        return np.asarray(self.estimador.predict_proba(x)[:, 1], dtype="float64")


def treinar_filtro(x: np.ndarray, apertado: np.ndarray) -> FiltroApertado:
    y = apertado.astype("int64")
    if len(np.unique(y)) < 2:
        raise ErroTreino("filtro: precisa de operações apertadas e firmes; só há uma classe")
    return FiltroApertado(HistGradientBoostingClassifier(**HIPERPARAMETROS).fit(x, y))


def escolher_limiar_filtro(
    p_dir: np.ndarray,
    p_ap: np.ndarray,
    alvo: np.ndarray,
    limiar: float,
    quantis: Sequence[float] = (0.9, 0.75, 0.5),
    n_minimo: int = 100,
) -> float:
    """Limiar de ``p_apertado`` (opera só com ``p_ap <= limiar``); ``inf`` = sem filtro."""
    direcao = np.where(p_dir >= limiar, 1, np.where(p_dir <= 1 - limiar, -1, 0))
    decidida = (direcao != 0) & ~np.isnan(alvo)
    acerto = ((direcao == 1) & (alvo == 1)) | ((direcao == -1) & (alvo == 0))
    candidatos = [math.inf] + [float(np.quantile(p_ap, q)) for q in sorted(quantis, reverse=True)]
    melhor, melhor_wilson = math.inf, -math.inf
    for c in candidatos:
        m = decidida & (p_ap <= c)
        n = int(m.sum())
        if n < n_minimo:
            continue
        inf, _ = wilson(int(acerto[m].sum()), n)
        if inf > melhor_wilson:
            melhor, melhor_wilson = c, inf
    return melhor
