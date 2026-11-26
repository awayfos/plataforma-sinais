import pandas as pd

from sinais.features.fs2 import (
    FEATURE_SET_VERSION_FS2,
    combinar_fs2,
    features_calendario,
    montar_snapshot_fs2,
)
from sinais.features.microestrutura import agregar_segundos, features_microestrutura
from sinais.features.snapshot import FEATURE_SET_VERSION, montar_snapshot

from .sinteticos_1s import para_1m, passeio_1s

T9 = 1795597200000  # 2026-11-25T09:00:00Z (quarta-feira)


def test_colunas_fs2_e_fs1_intacto() -> None:
    s1 = passeio_1s(400)
    m1 = para_1m(s1)
    fs2 = montar_snapshot_fs2(m1, s1)
    fs1 = montar_snapshot(m1)
    assert FEATURE_SET_VERSION == "fs-1"
    assert FEATURE_SET_VERSION_FS2 == "fs-2"
    mic = [c for c in fs2.columns if c.startswith("mic_")]
    cal = [c for c in fs2.columns if c.startswith("cal_")]
    assert list(fs2.columns) == list(fs1.columns) + mic + cal
    assert len(mic) == 17
    assert cal == ["cal_hora", "cal_min_hora", "cal_dia_semana"]
    pd.testing.assert_frame_equal(fs2[fs1.columns], fs1)
    assert fs2.index.equals(m1.index)


def test_calendario_usa_o_instante_de_decisao() -> None:
    # minuto que abre 09:59 decide às 10:00
    cal = features_calendario(pd.Index([T9 + 59 * 60_000]))
    assert cal.iloc[0].tolist() == [10.0, 0.0, 2.0]


def test_minuto_sem_segundos_fica_nan() -> None:
    s1 = passeio_1s(30)
    m1 = para_1m(s1)
    micro = features_microestrutura(agregar_segundos(s1[s1.index < s1.index[0] + 20 * 60_000]))
    fs2 = combinar_fs2(montar_snapshot(m1), micro)
    assert fs2["mic_vol_real_bps"].iloc[25:].isna().all()
    assert fs2["mic_vol_real_bps"].iloc[:20].notna().all()
