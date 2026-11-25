"""Treino do classificador e calibração isotônica em período separado."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.frozen import FrozenEstimator

HIPERPARAMETROS: dict[str, Any] = {
    "max_iter": 200,
    "learning_rate": 0.05,
    "max_leaf_nodes": 31,
    "l2_regularization": 1.0,
    "early_stopping": False,
    "random_state": 0,
}


class ErroTreino(ValueError):
    """Dados insuficientes para treinar ou calibrar."""


def colunas_modelo(snapshot: pd.DataFrame) -> list[str]:
    """Features usadas pelo modelo: tudo menos a idade do contexto (metadado de auditoria)."""
    return [c for c in snapshot.columns if not c.endswith("idade_ctx")]


@dataclass
class ModeloCalibrado:
    estimador: Any

    def probabilidade(self, x: np.ndarray) -> np.ndarray:
        """Probabilidade calibrada de alta."""
        return np.asarray(self.estimador.predict_proba(x)[:, 1], dtype="float64")


def _checar(y: np.ndarray, nome: str) -> None:
    if len(np.unique(y)) < 2:
        raise ErroTreino(f"{nome}: precisa de altas e baixas; só há uma classe")


def treinar(x: np.ndarray, y: np.ndarray, x_cal: np.ndarray, y_cal: np.ndarray) -> ModeloCalibrado:
    _checar(y, "treino")
    _checar(y_cal, "calibração")
    base = HistGradientBoostingClassifier(**HIPERPARAMETROS).fit(x, y)
    calibrado = CalibratedClassifierCV(FrozenEstimator(base), method="isotonic").fit(x_cal, y_cal)
    return ModeloCalibrado(calibrado)


def ece(p: np.ndarray, y: np.ndarray, faixas: int = 10) -> float:
    """Erro de calibração esperado: média ponderada de |frequência real − probabilidade|."""
    if len(p) == 0:
        return float("nan")
    idx = np.minimum((p * faixas).astype(int), faixas - 1)
    total = 0.0
    for b in range(faixas):
        m = idx == b
        if m.any():
            total += m.mean() * abs(float(y[m].mean()) - float(p[m].mean()))
    return total
