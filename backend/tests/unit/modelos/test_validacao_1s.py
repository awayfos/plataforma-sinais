import numpy as np
import pandas as pd

from sinais.backtest.precos import SeriePrecos
from sinais.core.dominio import Expiracao
from sinais.corretoras.regras import EXNOVA
from sinais.modelos.decisao import validar_com_1s

T0 = 1795575600000
M = 60_000


def precos_1s(subindo: bool) -> SeriePrecos:
    n = 400 * 60
    passo = 0.001 if subindo else -0.001
    c = 100 + passo * np.arange(n)
    idx = pd.Index(T0 + np.arange(n) * 1000, name="abertura")
    return SeriePrecos.de_quadro(pd.DataFrame({"o": c, "c": c}, index=idx), 1000)


SINAIS = pd.DataFrame({"decisao": [T0 + i * 2 * M for i in range(1, 160)], "direcao": 1})


def test_confirma_quando_o_holdout_realista_ganha() -> None:
    m, ok = validar_com_1s(SINAIS, precos_1s(True), EXNOVA.regras[Expiracao.M1], 0.86)
    assert m.wins + m.losses >= 100
    assert ok is True


def test_reprova_quando_o_holdout_realista_perde() -> None:
    m, ok = validar_com_1s(SINAIS, precos_1s(False), EXNOVA.regras[Expiracao.M1], 0.86)
    assert ok is False
    assert m.taxa < 0.5
