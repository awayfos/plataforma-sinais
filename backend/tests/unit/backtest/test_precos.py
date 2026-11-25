import pandas as pd

from sinais.backtest.precos import SeriePrecos

from ..analise.sinteticos import T0, M, quadro


def test_1s_exato() -> None:
    idx = pd.Index([T0, T0 + 1000, T0 + 2000], name="abertura")
    df = pd.DataFrame({"o": [1.0, 2, 3], "c": [1.5, 2.5, 3.5]}, index=idx)
    s = SeriePrecos.de_quadro(df, 1000)
    assert s.preco_em(T0 + 2000) == 2.5
    assert s.preco_em(T0 + 3000) == 3.5
    assert s.granularidade_ms == 1000


def test_1m_na_fronteira() -> None:
    s = SeriePrecos.de_quadro(quadro([10.0, 11, 12]), M)
    assert s.preco_em(T0 + M) == 10.0  # abertura do minuto que começa em T0+M
    assert s.preco_em(T0 + 3 * M) == 12.0  # fechamento do último minuto


def test_1m_dentro_do_minuto_none() -> None:
    assert SeriePrecos.de_quadro(quadro([10.0, 11]), M).preco_em(T0 + 30_000) is None


def test_lacuna_none() -> None:
    df = quadro([10.0, 11, 12, 13]).drop(T0 + 2 * M)
    s = SeriePrecos.de_quadro(df, M)
    assert s.preco_em(T0 + 5 * M) is None
