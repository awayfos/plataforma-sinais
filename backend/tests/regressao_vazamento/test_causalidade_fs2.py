"""Regressão de vazamento do ``fs-2``: a linha do minuto t só pode usar segundos que fecham
até o fim do minuto t (o instante de decisão), e nada depois.

Validado por mutação: trocar uma janela por ``.shift(-1)`` em ``microestrutura.py`` faz estes
testes falharem (ver ``docs/fases/fase-06b-modelo-v2.md``).
"""

import numpy as np
import pandas as pd

from sinais.features.fs2 import montar_snapshot_fs2

from ..unit.features.sinteticos_1s import para_1m, passeio_1s

M = 60_000
S1 = passeio_1s(500, semente=21)
# preço parado por 5 minutos (minutos 300 a 304): exercita "segundos desde a mudança"
S1.iloc[18_000:18_300, S1.columns.get_indexer(["o", "h", "l", "c"])] = S1["c"].iloc[17_999]
S1 = S1.drop(S1.index[12_000:12_090])  # lacuna de 90 s
M1 = para_1m(S1)
COMPLETO = montar_snapshot_fs2(M1, S1)
PARADO = int(np.searchsorted(M1.index, S1.index[0] + 302 * M))
SORTEADOS = np.random.default_rng(4).choice(np.arange(100, len(M1) - 1), 5, replace=False)
INSTANTES = sorted([PARADO, *SORTEADOS.tolist()])


def _diferentes(a: pd.Series, b: pd.Series) -> list[str]:
    x, y = a.to_numpy(dtype="float64"), b.to_numpy(dtype="float64")
    return [str(c) for c in a.index[~np.isclose(x, y, rtol=1e-9, atol=1e-12, equal_nan=True)]]


def _cortar(pos: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    fim = int(M1.index[pos]) + M
    return M1.iloc[: pos + 1], S1[S1.index < fim]


def test_cobertura_micro_ativa() -> None:
    assert COMPLETO.iloc[PARADO]["mic_seg_desde_mudanca"] > 60
    linha = COMPLETO.iloc[int(SORTEADOS[0])]
    mic = [c for c in COMPLETO.columns if c.startswith("mic_")]
    assert linha[mic].notna().sum() >= 15


def test_linha_t_igual_com_segundos_cortados_no_fim_do_minuto() -> None:
    for pos in INSTANTES:
        m1, s1 = _cortar(pos)
        diferentes = _diferentes(COMPLETO.iloc[pos], montar_snapshot_fs2(m1, s1).iloc[-1])
        assert diferentes == [], f"posição {pos}: colunas usam o futuro: {diferentes}"


def test_linha_t_nao_muda_com_segundos_futuros_embaralhados() -> None:
    rng = np.random.default_rng(8)
    pos = PARADO
    fim = int(M1.index[pos]) + M
    s1 = S1.copy()
    futuro = s1.index >= fim
    s1.loc[futuro] = s1.loc[futuro].to_numpy()[rng.permutation(int(futuro.sum()))]
    m1 = M1.copy()
    m1.iloc[pos + 1 :] = m1.iloc[pos + 1 :].to_numpy()[rng.permutation(len(m1) - pos - 1)]
    diferentes = _diferentes(COMPLETO.iloc[pos], montar_snapshot_fs2(m1, s1).iloc[pos])
    assert diferentes == [], f"colunas mudam com o futuro: {diferentes}"
