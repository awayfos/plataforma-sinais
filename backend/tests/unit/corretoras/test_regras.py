from datetime import UTC, datetime

import pytest

from sinais.core.dominio import Direcao, Expiracao
from sinais.core.tempo import de_datetime
from sinais.corretoras.regras import EXNOVA, Resultado, liquidar, ponto_equilibrio


def t(h: int, m: int, s: int = 0, ms: int = 0) -> int:
    return de_datetime(datetime(2026, 11, 25, h, m, s, ms * 1000, tzinfo=UTC))


UM = EXNOVA.regras[Expiracao.M1]
QUINZE = EXNOVA.regras[Expiracao.M15]


@pytest.mark.parametrize(
    ("compra", "vencimento"),
    [
        (t(0, 30, 10), t(0, 31)),
        (t(0, 30, 29, 999), t(0, 31)),
        (t(0, 30, 30), t(0, 32)),
        (t(0, 30, 35), t(0, 32)),
        (t(0, 30, 0), t(0, 31)),
    ],
)
def test_vencimento_1min(compra: int, vencimento: int) -> None:
    assert UM.vencimento_para(compra) == vencimento


def test_vencimento_15min() -> None:
    assert QUINZE.vencimento_para(t(0, 39, 59)) == t(0, 45)
    assert QUINZE.vencimento_para(t(0, 40, 0)) == t(1, 0)
    assert QUINZE.prazo_compra(t(0, 45)) == t(0, 39, 59, 999)


def test_perfil_exnova_hipoteses_declaradas() -> None:
    assert set(EXNOVA.regras) == set(Expiracao)
    assert EXNOVA.hipoteses == frozenset({Expiracao.M5, Expiracao.M30, Expiracao.H1})
    assert all(0 < p < 1 for p in EXNOVA.payout.values())


def test_liquidar() -> None:
    assert liquidar(Direcao.COMPRA, 100.0, 100.5) is Resultado.WIN
    assert liquidar(Direcao.COMPRA, 100.0, 99.5) is Resultado.LOSS
    assert liquidar(Direcao.VENDA, 100.0, 99.5) is Resultado.WIN
    assert liquidar(Direcao.VENDA, 100.0, 100.0) is Resultado.TIE


def test_ponto_equilibrio() -> None:
    assert ponto_equilibrio(0.85) == pytest.approx(0.54054, abs=1e-5)
    assert ponto_equilibrio(0.80) == pytest.approx(0.55556, abs=1e-5)
