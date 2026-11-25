"""Regressão de vazamento: a linha t do snapshot não pode depender de nada depois de t.

Dados sintéticos com 12.000 minutos (200 candles de 1h), uma lacuna e um trecho sem volume.
"""

import numpy as np
import pandas as pd

from sinais.features.snapshot import JANELA_AO_VIVO_1M, montar_snapshot

from ..unit.analise.sinteticos import passeio

N = 12_000
DF = passeio(N, semente=11)
DF.iloc[7000:7030, DF.columns.get_indexer(["v", "vb"])] = 0.0
DF = DF.drop(DF.index[6000])
COMPLETO = montar_snapshot(DF)
INSTANTES = sorted(np.random.default_rng(3).choice(np.arange(8000, len(DF) - 1), 6, replace=False))


def _diferentes(a: pd.Series, b: pd.Series, rtol: float = 1e-9) -> list[str]:
    x, y = a.to_numpy(dtype="float64"), b.to_numpy(dtype="float64")
    ruins = ~np.isclose(x, y, rtol=rtol, atol=1e-9, equal_nan=True)
    return [str(c) for c in a.index[ruins]]


def test_cobertura_h1_ativa() -> None:
    linha = COMPLETO.iloc[INSTANTES[0]]
    assert not np.isnan(linha["h1_ind_ema50_dist"])
    assert not np.isnan(linha["h1_ind_ich_span_b"])


def test_linha_t_igual_com_dados_cortados_em_t() -> None:
    for pos in INSTANTES:
        cortado = montar_snapshot(DF.iloc[: pos + 1]).iloc[-1]
        diferentes = _diferentes(COMPLETO.iloc[pos], cortado)
        assert diferentes == [], f"posição {pos}: colunas usam o futuro: {diferentes}"


def test_linha_t_nao_muda_com_futuro_embaralhado() -> None:
    rng = np.random.default_rng(5)
    pos = INSTANTES[0]
    mexido = DF.copy()
    futuro = mexido.iloc[pos + 1 :].to_numpy()
    mexido.iloc[pos + 1 :] = futuro[rng.permutation(len(futuro))]
    diferentes = _diferentes(COMPLETO.iloc[pos], montar_snapshot(mexido).iloc[pos])
    assert diferentes == [], f"colunas mudam com o futuro: {diferentes}"


def test_janela_ao_vivo_reproduz_o_historico() -> None:
    """Ao vivo calcula sobre JANELA_AO_VIVO_1M minutos; o resultado tem de bater com o histórico."""
    longo = passeio(JANELA_AO_VIVO_1M + 6000, semente=13)
    completo = montar_snapshot(longo).iloc[-1]
    janela = montar_snapshot(longo.iloc[-JANELA_AO_VIVO_1M:]).iloc[-1]
    diferentes = _diferentes(completo, janela, rtol=1e-3)
    assert diferentes == [], f"janela ao vivo diverge do histórico em: {diferentes}"
