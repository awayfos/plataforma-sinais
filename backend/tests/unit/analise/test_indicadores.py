import math
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from sinais.analise import indicadores as ind
from sinais.analise.quadro import para_quadro
from sinais.dados.modelos import Candle

from .sinteticos import T0, quadro


def test_para_quadro() -> None:
    c = Candle(
        "BTCUSDT",
        60_000,
        T0,
        Decimal("1.5"),
        Decimal("2"),
        Decimal("1"),
        Decimal("1.75"),
        Decimal("10"),
        Decimal("15"),
        3,
        Decimal("4"),
        "teste",
    )
    df = para_quadro([c])
    assert list(df.columns) == ["o", "h", "l", "c", "v", "vb"]
    assert df.index.name == "abertura"
    assert df.loc[T0, "c"] == 1.75
    assert df["c"].dtype == "float64"


def test_sma() -> None:
    s = pd.Series([1.0, 2, 3, 4, 5, 6])
    assert ind.sma(s, 3).tolist()[2:] == [2.0, 3.0, 4.0, 5.0]
    assert ind.sma(s, 3).isna().tolist()[:2] == [True, True]


def test_ema_semeada_pela_sma() -> None:
    s = pd.Series([1.0, 2, 3, 4, 5, 6])
    e = ind.ema(s, 3)
    assert math.isnan(e[1])
    assert e[2] == pytest.approx(2.0)
    assert e[3] == pytest.approx(3.0)
    assert e[5] == pytest.approx(5.0)


def test_rma_wilder() -> None:
    s = pd.Series([2.0, 4, 6, 8])
    r = ind.rma(s, 2)
    assert r.tolist()[1:] == pytest.approx([3.0, 4.5, 6.25])


def test_rsi_serie_crescente_100() -> None:
    r = ind.rsi(pd.Series(np.arange(30, dtype="float64")), 14)
    assert r.iloc[-1] == pytest.approx(100.0)


def test_rsi_constante_50() -> None:
    r = ind.rsi(pd.Series([5.0] * 30), 14)
    assert r.iloc[-1] == pytest.approx(50.0)


def test_rsi_wilder_caso_conhecido() -> None:
    c = pd.Series([10.0, 11, 10, 12, 11])
    # variações: +1 -1 +2 -1 ; n=2: ganho0 = (1+0)/2 = .5, perda0 = (0+1)/2 = .5
    # t=3: ganho = (.5*1 + 2)/2 = 1.25, perda = (.5*1 + 0)/2 = .25 -> RS 5 -> RSI 83.333
    # t=4: ganho = 1.25/2 = .625, perda = (.25 + 1)/2 = .625 -> RSI 50
    r = ind.rsi(c, 2)
    assert r[2] == pytest.approx(50.0)
    assert r[3] == pytest.approx(100 - 100 / 6)
    assert r[4] == pytest.approx(50.0)


def test_macd_hist_igual_macd_menos_sinal() -> None:
    df = ind.macd(pd.Series(np.linspace(1, 50, 80)))
    ultimo = df.iloc[-1]
    assert ultimo["hist"] == pytest.approx(ultimo["macd"] - ultimo["sinal"])
    assert ultimo["macd"] > 0


def test_bollinger_populacional() -> None:
    b = ind.bollinger(pd.Series([1.0, 2, 3]), n=3, k=2)
    desvio = np.std([1, 2, 3])
    assert b["media"][2] == 2.0
    assert b["sup"][2] == pytest.approx(2 + 2 * desvio)
    assert b["largura"][2] == pytest.approx(4 * desvio / 2)


def test_atr_true_range_com_gap() -> None:
    df = pd.DataFrame({"h": [10.0, 15, 16], "l": [9.0, 14, 15], "c": [9.5, 14.5, 15.5]})
    tr = ind.true_range(df)
    assert tr.tolist() == [1.0, 5.5, 1.5]
    assert ind.atr(df, 2)[1] == pytest.approx(3.25)


def test_adx_tendencia_forte_maior_que_lateral() -> None:
    tendencia = ind.adx(quadro(np.linspace(100, 200, 120)), 14)["adx"].iloc[-1]
    lateral = ind.adx(quadro(100 + 3 * np.sin(np.arange(120) / 3)), 14)["adx"].iloc[-1]
    assert tendencia > 50 > lateral


def test_adx_constante_sem_inf() -> None:
    a = ind.adx(quadro([100.0] * 60, amplitude=0.0), 14)
    assert not np.isinf(a.to_numpy()).any()


def test_estocastico_limites_e_constante() -> None:
    e = ind.estocastico(quadro(np.sin(np.arange(100) / 5) * 10 + 100))
    validos = e.dropna()
    assert ((validos >= 0) & (validos <= 100)).all().all()
    const = ind.estocastico(quadro([100.0] * 40, amplitude=0.0))
    assert const["k"].iloc[-1] == pytest.approx(50.0)


def test_ichimoku_spans_deslocadas() -> None:
    df = quadro(np.linspace(100, 200, 200))
    ich = ind.ichimoku(df, 9, 26, 52)
    base = (ich["tenkan"] + ich["kijun"]) / 2
    assert ich["span_a"].iloc[-1] == pytest.approx(base.iloc[-1 - 26])


def test_aquecimento_nan() -> None:
    r = ind.rsi(pd.Series([1.0, 2, 3]), 14)
    assert r.isna().all()
