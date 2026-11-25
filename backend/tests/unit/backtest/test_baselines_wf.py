from datetime import UTC, datetime

import pandas as pd

from sinais.backtest.baselines import aleatoria, seguir_ultimo, sempre_compra, sempre_venda
from sinais.backtest.walk_forward import dobras, purgar
from sinais.core.tempo import de_datetime

from ..analise.sinteticos import T0, M, quadro


def d(a: int, m: int, dia: int = 1) -> int:
    return de_datetime(datetime(a, m, dia, tzinfo=UTC))


DF = quadro([100.0, 101, 101, 100, 102])


def test_sempre_compra_e_venda() -> None:
    s = sempre_compra(DF)
    assert s["decisao"].tolist() == [T0 + (i + 1) * M for i in range(5)]
    assert set(s["direcao"]) == {1}
    assert set(sempre_venda(DF)["direcao"]) == {-1}


def test_seguir_ultimo_ignora_doji() -> None:
    s = seguir_ultimo(DF)
    assert s["direcao"].tolist() == [1, -1, 1]
    assert s["decisao"].tolist() == [T0 + 2 * M, T0 + 4 * M, T0 + 5 * M]


def test_aleatoria_reprodutivel() -> None:
    a, b = aleatoria(DF, semente=1, prob=0.6), aleatoria(DF, semente=1, prob=0.6)
    pd.testing.assert_frame_equal(a, b)
    assert set(a["direcao"]) <= {1, -1}


def test_dobras_mensais_sem_sobreposicao() -> None:
    ds = dobras(d(2025, 1), d(2026, 1), treino_meses=6, calibracao_meses=1, teste_meses=1)
    assert len(ds) == 5
    primeira = ds[0]
    assert primeira.treino == (d(2025, 1), d(2025, 7))
    assert primeira.calibracao == (d(2025, 7), d(2025, 8))
    assert primeira.teste == (d(2025, 8), d(2025, 9))
    assert ds[-1].teste == (d(2025, 12), d(2026, 1))
    for x in ds:
        assert x.treino[1] <= x.calibracao[0] < x.calibracao[1] <= x.teste[0]


def test_purga_remove_rotulo_que_cruza_o_teste() -> None:
    ate = d(2025, 8)
    dec = pd.Series([ate - 80 * M, ate - 70 * M, ate - 5 * M])
    mantidos = purgar(dec, horizonte_ms=15 * M, ate=ate, embargo_ms=60 * M)
    assert mantidos.tolist() == [True, False, False]
