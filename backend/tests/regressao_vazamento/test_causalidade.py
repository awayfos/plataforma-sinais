"""Regressão de vazamento: a linha t do snapshot não pode depender de nada depois de t."""

import numpy as np
import pandas as pd

from sinais.features.snapshot import montar_snapshot

from ..unit.analise.sinteticos import passeio

N = 3000
DF = passeio(N, semente=11)
COMPLETO = montar_snapshot(DF)
INSTANTES = sorted(np.random.default_rng(3).choice(np.arange(200, N - 1), 20, replace=False))


def _iguais(a: pd.Series, b: pd.Series) -> list[str]:
    x, y = a.to_numpy(dtype="float64"), b.to_numpy(dtype="float64")
    ruins = ~np.isclose(x, y, rtol=1e-9, atol=1e-12, equal_nan=True)
    return [str(c) for c in a.index[ruins]]


def test_linha_t_igual_com_dados_cortados_em_t() -> None:
    for pos in INSTANTES:
        cortado = montar_snapshot(DF.iloc[: pos + 1]).iloc[-1]
        diferentes = _iguais(COMPLETO.iloc[pos], cortado)
        assert diferentes == [], f"posição {pos}: colunas usam o futuro: {diferentes}"


def test_linha_t_nao_muda_com_futuro_embaralhado() -> None:
    rng = np.random.default_rng(5)
    for pos in INSTANTES[:5]:
        mexido = DF.copy()
        futuro = mexido.iloc[pos + 1 :].to_numpy()
        mexido.iloc[pos + 1 :] = futuro[rng.permutation(len(futuro))]
        diferentes = _iguais(COMPLETO.iloc[pos], montar_snapshot(mexido).iloc[pos])
        assert diferentes == [], f"posição {pos}: colunas mudam com o futuro: {diferentes}"
