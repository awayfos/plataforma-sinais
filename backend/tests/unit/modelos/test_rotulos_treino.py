import numpy as np
import pandas as pd
import pytest

from sinais.backtest.precos import SeriePrecos
from sinais.core.dominio import Expiracao
from sinais.corretoras.regras import EXNOVA
from sinais.modelos.rotulos import rotular
from sinais.modelos.treino import ErroTreino, colunas_modelo, ece, treinar

from ..analise.sinteticos import T0, M, quadro

UM = EXNOVA.regras[Expiracao.M1]


def test_rotulos_alta_baixa_empate_e_fim() -> None:
    df = quadro([100.0, 101, 100, 100, 102])
    r = rotular(df, UM, SeriePrecos.de_quadro(df, M))
    # decisão no fechamento de cada minuto; entrada = abertura do minuto seguinte
    assert r["decisao"].tolist() == [T0 + (i + 1) * M for i in range(5)]
    assert r["vencimento_t"].tolist()[0] == T0 + 2 * M
    alvo = r["alvo"].tolist()
    assert alvo[0] == 1.0  # 100 -> 101
    assert alvo[1] == 0.0  # 101 -> 100
    assert np.isnan(alvo[2])  # empate 100 -> 100
    assert np.isnan(alvo[4])  # vencimento depois do fim dos dados


def test_colunas_modelo_exclui_idade() -> None:
    snap = pd.DataFrame({"ind_rsi": [1.0], "h1_idade_ctx": [3.0], "m5_ind_rsi": [2.0]})
    assert colunas_modelo(snap) == ["ind_rsi", "m5_ind_rsi"]


def _dados(n: int, semente: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(semente)
    y = rng.integers(0, 2, n)
    x = np.column_stack([y + rng.normal(0, 0.5, n), rng.normal(size=n)])
    return x.astype("float32"), y


def test_aprende_sinal_e_calibra() -> None:
    x, y = _dados(3000, 1)
    xc, yc = _dados(1500, 2)
    xt, yt = _dados(1500, 3)
    m = treinar(x, y, xc, yc)
    p = m.probabilidade(xt)
    acerto = ((p > 0.5) == (yt == 1)).mean()
    assert acerto > 0.8
    assert ece(p, yt) < 0.05


def test_classe_unica_erro_claro() -> None:
    x = np.zeros((50, 2), dtype="float32")
    with pytest.raises(ErroTreino):
        treinar(x, np.ones(50, dtype="int64"), x, np.ones(50, dtype="int64"))


def test_ece_perfeito_zero() -> None:
    p = np.array([0.0, 0.0, 1.0, 1.0])
    assert ece(p, np.array([0, 0, 1, 1])) == pytest.approx(0.0)


def test_vencimentos_vetorizados_iguais_a_regra() -> None:
    from sinais.modelos.rotulos import vencimentos

    ts = np.array([T0 + s * 1000 for s in range(0, 200, 7)])
    for regra in EXNOVA.regras.values():
        assert vencimentos(ts, regra).tolist() == [regra.vencimento_para(int(t)) for t in ts]
