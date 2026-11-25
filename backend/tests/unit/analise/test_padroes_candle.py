import numpy as np
import pandas as pd

from sinais.analise import padroes_candle as pc


def velas(*ohlc: tuple[float, float, float, float]) -> pd.DataFrame:
    o, h, l, c = zip(*ohlc, strict=True)  # noqa: E741
    return pd.DataFrame({"o": o, "h": h, "l": l, "c": c, "v": 10.0, "vb": 6.0})


def test_doji() -> None:
    assert pc.doji(velas((10, 11, 9, 10.05), (10, 11, 9, 10.8))).tolist() == [True, False]


def test_martelo_e_estrela_cadente() -> None:
    df = velas((10, 10.1, 8, 10.05), (10, 12, 9.85, 9.9))
    assert pc.martelo(df).tolist() == [True, False]
    assert pc.estrela_cadente(df).tolist() == [False, True]


def test_pin_bar() -> None:
    df = velas((10, 10.2, 7, 10.1), (10, 13, 9.9, 9.95), (10, 11, 9, 10.5))
    assert pc.pin_bar(df).tolist() == [1, -1, 0]


def test_engolfo() -> None:
    alta = velas((10, 10.2, 8.8, 9), (8.9, 11.2, 8.8, 11))
    baixa = velas((9, 11.2, 8.8, 11), (11.1, 11.2, 8.5, 8.7))
    nada = velas((10, 10.2, 8.8, 9), (9.2, 9.8, 9.1, 9.5))
    assert pc.engolfo(alta).tolist() == [0, 1]
    assert pc.engolfo(baixa).tolist() == [0, -1]
    assert pc.engolfo(nada).tolist() == [0, 0]


def test_marubozu() -> None:
    df = velas((10, 12, 10, 12), (12, 12, 10, 10), (10, 13, 9, 12))
    assert pc.marubozu(df).tolist() == [1, -1, 0]


def test_inside_e_outside_bar() -> None:
    df = velas((10, 12, 8, 11), (10, 11, 9, 10.5), (10, 13, 7, 9))
    assert pc.inside_bar(df).tolist() == [False, True, False]
    assert pc.outside_bar(df).tolist() == [False, False, True]


def test_estrela_da_manha_e_da_tarde() -> None:
    manha = velas((12, 12.1, 9.9, 10), (9.9, 10, 9.5, 9.8), (9.9, 11.6, 9.8, 11.5))
    tarde = velas((10, 12.1, 9.9, 12), (12.1, 12.5, 12, 12.2), (12.1, 12.2, 10.4, 10.5))
    assert pc.estrela_manha(manha).tolist() == [False, False, True]
    assert pc.estrela_tarde(tarde).tolist() == [False, False, True]
    assert not pc.estrela_manha(tarde).any()


def test_sequencia_com_sinal() -> None:
    df = velas(
        (1, 2, 0.5, 1.5), (1.5, 2.5, 1, 2), (2, 2.5, 1, 1.2), (1.2, 2, 1, 1.1), (1, 2, 0.5, 1.8)
    )
    assert pc.sequencia(df).tolist() == [1, 2, -1, -2, 1]


def test_forca() -> None:
    f = pc.forca(velas((10, 12, 8, 11)))
    assert f["corpo_rel"][0] == 0.25
    assert abs(f["pressao_compradora"][0] - 0.1) < 1e-12


def test_amplitude_zero_nao_quebra() -> None:
    df = velas((10, 10, 10, 10))
    df["v"] = 0.0
    assert pc.pin_bar(df).tolist() == [0]
    assert not pc.doji(df).any()
    f = pc.forca(df)
    assert np.isnan(f["corpo_rel"][0]) and np.isnan(f["pressao_compradora"][0])
