import math

import numpy as np
import pandas as pd
import pytest

from sinais.analise import volume as vol
from sinais.analise.fibonacci import niveis_fibonacci, posicao_fibonacci
from sinais.analise.regioes import regioes

from .sinteticos import T0, M, quadro


def test_volume_relativo() -> None:
    df = quadro([1.0, 1, 1, 1])
    df["v"] = [10.0, 10, 10, 40]
    assert vol.volume_relativo(df, 3).iloc[3] == pytest.approx(2.0)


def test_volume_zero_nan() -> None:
    df = quadro([1.0] * 30)
    df["v"] = 0.0
    df["vb"] = 0.0
    assert vol.volume_relativo(df, 20).isna().all()
    assert vol.pressao_acumulada(df, 20).isna().all()
    assert vol.vwap(df).isna().all()
    assert not np.isinf(vol.expansao_volume(df, 20).to_numpy()).any()


def test_pressao_acumulada() -> None:
    df = quadro([1.0, 1])
    df["v"], df["vb"] = [10.0, 10], [8.0, 6]
    assert vol.pressao_acumulada(df, 2).iloc[1] == pytest.approx((6 + 2) / 20)


def test_divergencia_volume() -> None:
    df = quadro(np.linspace(100, 110, 40))
    df["v"] = np.linspace(40, 10, 40)
    assert vol.divergencia_volume(df, 10).iloc[-1] == -1


def test_vwap_reinicia_no_dia() -> None:
    dia = 86_400_000
    inicio = T0 - T0 % dia
    idx = pd.Index([inicio + dia - 2 * M, inicio + dia - M, inicio + dia], name="abertura")
    df = pd.DataFrame(
        {
            "o": [10.0, 10, 20],
            "h": [10.0, 10, 20],
            "l": [10.0, 10, 20],
            "c": [10.0, 10, 20],
            "v": [1.0, 3, 2],
            "vb": [0.5, 1.5, 1],
        },
        index=idx,
    )
    v = vol.vwap(df)
    assert v.iloc[1] == pytest.approx(10.0)
    assert v.iloc[2] == pytest.approx(20.0)


def vela(h: float, c: float) -> tuple[float, float, float, float]:
    return (c, h, h - 1, c)


def test_regioes_toques_falso_rompimento_e_rompimento() -> None:
    dados = [
        vela(9, 8.5),
        vela(10, 9.5),
        vela(9, 8.5),
        vela(10, 9.5),
        vela(9, 8.5),
        vela(9.5, 9),
        (9, 10.5, 9, 9.8),
        (9.8, 10.6, 9.7, 10.4),
    ]
    o, h, lo, c = zip(*dados, strict=True)
    df = pd.DataFrame({"o": o, "h": h, "l": lo, "c": c, "v": 1.0, "vb": 0.5})
    r = regioes(df, k=1, tolerancia_atr=0.5, n_atr=2)
    assert r["res_toques"].iloc[5] == 2
    assert r["res_dist"].iloc[5] > 0
    assert r["falso_rompimento"].tolist()[6] == 1
    assert r["rompimento"].tolist()[7] == 1
    assert r["rompimento"].tolist()[:7] == [0] * 7


def test_niveis_fibonacci() -> None:
    n = niveis_fibonacci(110.0, 100.0)
    assert n["0"] == 110.0
    assert n["100"] == 100.0
    assert n["61.8"] == pytest.approx(103.82)
    assert list(n) == ["0", "23.6", "38.2", "50", "61.8", "78.6", "100"]


def test_posicao_fibonacci_entre_0_e_1() -> None:
    p = posicao_fibonacci(quadro(100 + 5 * np.sin(np.arange(200) / 6)), k=3).dropna()
    assert len(p) > 0
    assert not math.isinf(p.max())
