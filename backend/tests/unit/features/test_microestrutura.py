import numpy as np
import pandas as pd

from sinais.features.microestrutura import (
    JANELA_AO_VIVO_MICRO_MIN,
    AgregadorMicro,
    agregar_segundos,
    features_microestrutura,
)

from ..analise.sinteticos import T0
from .sinteticos_1s import passeio_1s, segundos

M = 60_000


def _tres_minutos() -> pd.DataFrame:
    """Minuto 0 parado em 100; minuto 1 parado até 49 s, sobe 0,1 por segundo de 50 a 54 s e
    para em 100,5; minuto 2 parado em 100,5 e sem volume."""
    m1 = [100.0] * 50 + [100.1, 100.2, 100.3, 100.4, 100.5] + [100.5] * 5
    c = [100.0] * 60 + m1 + [100.5] * 60
    v = np.r_[np.ones(120), np.zeros(60)]
    vb = np.r_[np.full(110, 0.5), np.ones(10), np.zeros(60)]
    return segundos(c, v=v, vb=vb)


def test_minuto_conhecido() -> None:
    f = features_microestrutura(agregar_segundos(_tres_minutos()))
    assert f.index.tolist() == [T0, T0 + M, T0 + 2 * M]
    x = f.loc[T0 + M]
    assert np.isclose(x["mic_compra_min"], 35 / 60)
    assert np.isclose(x["mic_compra_ult10"], 1.0)
    assert np.isclose(x["mic_compra_delta"], 0.5)
    assert np.isclose(x["mic_frac_parados"], 55 / 60)
    assert x["mic_sequencia"] == 5
    assert x["mic_seg_desde_mudanca"] == 5
    r = np.diff(np.log([100.0, 100.1, 100.2, 100.3, 100.4, 100.5]))
    vol = np.sqrt((r**2).sum())
    assert np.isclose(x["mic_vol_real_bps"], vol * 1e4)
    assert np.isclose(x["mic_ret_ult10"], np.log(100.5 / 100) / vol)
    assert np.isclose(x["mic_ret_ult30"], np.log(100.5 / 100) / vol)
    assert np.isclose(x["mic_explosao_10s"], 1.0)
    assert x["mic_seg_presentes"] == 60


def test_segundos_desde_mudanca_atravessa_minuto() -> None:
    f = features_microestrutura(agregar_segundos(_tres_minutos()))
    assert f.loc[T0 + 2 * M, "mic_seg_desde_mudanca"] == 65
    assert f.loc[T0 + 2 * M, "mic_sequencia"] == 0
    assert np.isnan(f.loc[T0, "mic_seg_desde_mudanca"])


def test_minuto_sem_volume_ou_parado_vira_nan_sem_inf() -> None:
    f = features_microestrutura(agregar_segundos(_tres_minutos()))
    parado, sem_volume = f.loc[T0], f.loc[T0 + 2 * M]
    assert parado["mic_vol_real_bps"] == 0
    assert np.isnan(parado["mic_ret_ult10"])
    assert np.isnan(sem_volume["mic_compra_min"])
    assert np.isnan(sem_volume["mic_explosao_10s"])
    assert np.isfinite(f.to_numpy(dtype="float64")[~np.isnan(f.to_numpy(dtype="float64"))]).all()


def test_agregacao_em_partes_igual_a_inteira() -> None:
    df = passeio_1s(300)
    df = df.drop(df.index[[9000, 9001, 9002]])  # segundos faltando no meio da segunda parte
    corte = T0 + 150 * M
    ag = AgregadorMicro()
    ag.adicionar(df[df.index < corte])
    ag.adicionar(df[df.index >= corte])
    pd.testing.assert_frame_equal(ag.resultado(), agregar_segundos(df))


def test_janela_ao_vivo_reproduz_historico() -> None:
    agg = agregar_segundos(passeio_1s(400, semente=9))
    completo = features_microestrutura(agg).iloc[-1]
    janela = features_microestrutura(agg.iloc[-JANELA_AO_VIVO_MICRO_MIN:]).iloc[-1]
    pd.testing.assert_series_equal(completo, janela)
