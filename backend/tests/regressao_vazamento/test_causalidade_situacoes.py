"""Regressão de vazamento do motor de situações: os eventos com decisão até t (e todo o seu
contexto) só podem depender de candles de 1m que fecham até t.

Dois testes: série cortada exatamente no candle da decisão de um evento de cada variação, e
candles futuros embaralhados. Validado por mutação (ver ``docs/fases/fase-06c-situacoes.md``).
"""

import numpy as np
import pandas as pd

from sinais.situacoes.motor import detectar_todas

from ..unit.situacoes.sinteticos import M, passeio

SERIE = passeio(12_000, semente=8)
SERIE = SERIE.drop(SERIE.index[7000:7037])  # lacuna de 37 min
COMPLETO = detectar_todas(SERIE)
# um corte por variação, no candle da decisão do seu primeiro evento após o aquecimento
CORTES = sorted(
    int(np.searchsorted(SERIE.index, g["decisao"].iloc[len(g) // 2] - M))
    for _, g in COMPLETO.groupby("variacao")
)


def _ate(ev: pd.DataFrame, t: int) -> pd.DataFrame:
    return ev[ev["decisao"] <= t].reset_index(drop=True)


def test_cobertura_um_corte_por_variacao() -> None:
    assert len(CORTES) == 10


def test_eventos_iguais_com_a_serie_cortada_na_decisao() -> None:
    for pos in CORTES:
        t = int(SERIE.index[pos]) + M
        cortado = detectar_todas(SERIE.iloc[: pos + 1])
        pd.testing.assert_frame_equal(_ate(COMPLETO, t), _ate(cortado, t), check_exact=False)


def test_eventos_nao_mudam_com_o_futuro_embaralhado() -> None:
    rng = np.random.default_rng(3)
    for pos in CORTES[::3]:
        t = int(SERIE.index[pos]) + M
        df = SERIE.copy()
        futuro = df.iloc[pos + 1 :].to_numpy()
        df.iloc[pos + 1 :] = futuro[rng.permutation(len(futuro))]
        pd.testing.assert_frame_equal(
            _ate(COMPLETO, t), _ate(detectar_todas(df), t), check_exact=False
        )


def test_rompimentos_de_regiao_so_usam_pivos_confirmados() -> None:
    """Base de S2/S3: o rompimento no candle i (níveis e toques) não muda com a série cortada em i.
    Muitos cortes numa série curta, porque um pivô vazado só pesa se for rompido logo depois."""
    from sinais.situacoes.base import montar_base
    from sinais.situacoes.detectores import rompimentos

    curta = SERIE.iloc[:3000]
    completo = rompimentos(montar_base(curta), 3, 0.5, 240)
    for pos in [p for p in completo if p >= 300][:60]:
        cortado = rompimentos(montar_base(curta.iloc[: pos + 1]), 3, 0.5, 240)
        # repr: NaN em min_entre_toques não é igual a si mesmo
        assert repr(cortado.get(pos)) == repr(completo[pos]), f"candle {pos} usa o futuro"
