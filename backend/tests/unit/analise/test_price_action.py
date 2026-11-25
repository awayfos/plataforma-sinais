import numpy as np

from sinais.analise.price_action import price_action

from .sinteticos import quadro


def test_tendencia_alta_inclinacao_e_continuidade() -> None:
    pa = price_action(quadro(np.linspace(100, 160, 120)))
    assert pa["inclinacao_ema"].iloc[-1] > 0
    assert pa["continuidade"].iloc[-1] > 0.5
    assert pa["impulso"].iloc[-1] > 1


def test_desaceleracao_quando_o_movimento_freia() -> None:
    c = np.concatenate([100 + np.arange(101, dtype="float64"), 200 + 0.1 * np.arange(1, 31)])
    pa = price_action(quadro(c))
    assert pa["desaceleracao"].iloc[108] < 0


def test_lateral_em_mercado_estreito_apos_tendencia() -> None:
    c = np.concatenate([np.linspace(100, 250, 150), 250 + 0.2 * np.sin(np.arange(150))])
    pa = price_action(quadro(c, amplitude=0.3))
    assert bool(pa["lateral"].iloc[-1]) is True
    assert bool(pa["lateral"].iloc[140]) is False


def test_rejeicao_pavio_superior() -> None:
    df = quadro([100.0] * 30)
    df.loc[df.index[-1], "h"] = 105.0
    assert price_action(df)["rejeicao"].iloc[-1] > 0.5


def test_sem_inf_em_serie_constante() -> None:
    pa = price_action(quadro([100.0] * 80, amplitude=0.0))
    assert not np.isinf(pa.select_dtypes("number").to_numpy(dtype="float64")).any()
