import math

import pandas as pd
import pytest

from sinais.backtest.metricas import (
    benjamini_hochberg,
    calcular,
    por_grupo,
    pvalor_acima_equilibrio,
    wilson,
)


def ops(*resultados: str, t0: int = 0) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "resultado": list(resultados),
            "entrada_t": [t0 + i * 3_600_000 for i in range(len(resultados))],
        }
    )


def test_wilson_conhecido() -> None:
    inf, sup = wilson(8, 10)
    assert inf == pytest.approx(0.4902, abs=1e-4)
    assert sup == pytest.approx(0.9433, abs=1e-4)


def test_sem_operacoes_nan_sem_erro() -> None:
    m = calcular(ops(), payout=0.85)
    assert m.n == 0
    assert math.isnan(m.taxa) and math.isnan(m.wilson_inf) and math.isnan(m.valor_esperado)


def test_calcular_com_empates_e_fora() -> None:
    m = calcular(ops("WIN", "WIN", "LOSS", "TIE", "FORA_DA_JANELA", "SEM_DADO"), payout=0.8)
    assert (m.n, m.wins, m.losses, m.ties, m.fora_janela, m.sem_dado) == (4, 2, 1, 1, 1, 1)
    assert m.taxa == pytest.approx(2 / 3)
    assert m.valor_esperado == pytest.approx((2 * 0.8 - 1) / 4)
    assert m.p_equilibrio == pytest.approx(1 / 1.8)


def test_por_grupo_hora() -> None:
    g = por_grupo(
        ops("WIN", "LOSS", "WIN"), 0.85, lambda d: (d["entrada_t"] // 3_600_000 % 24).astype(str)
    )
    assert set(g) == {"0", "1", "2"}
    assert g["1"].losses == 1


def test_benjamini_hochberg() -> None:
    assert benjamini_hochberg([0.01, 0.04, 0.03, 0.005]) == [True] * 4
    assert benjamini_hochberg([0.01, 0.02, 0.03, 0.04, 0.05, 0.5]) == [False] * 6


def test_pvalor_binomial_exato() -> None:
    # P(X >= 9 | n=10, p=.5) = (10 + 1) / 1024
    assert pvalor_acima_equilibrio(9, 10, 0.5) == pytest.approx(11 / 1024)
    assert math.isnan(pvalor_acima_equilibrio(0, 0, 0.5))


def test_calcular_conta_apertados() -> None:
    df = ops("WIN", "WIN", "LOSS")
    df["apertado"] = [True, False, False]
    m = calcular(df, payout=0.85)
    assert m.apertados == 1
    assert m.taxa_sem_apertados == 0.5
