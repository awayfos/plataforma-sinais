from decimal import Decimal

from sinais.dados.conferencia import Divergencia, comparar

from .fabrica import T0, M, c1m


def test_iguais_sem_divergencia() -> None:
    a = [c1m(0), c1m(1)]
    assert comparar(a, list(a)) == []


def test_aponta_campo_diferente() -> None:
    oficial = [c1m(0, c="105")]
    nosso = [c1m(0, c="104")]
    assert comparar(oficial, nosso) == [
        Divergencia(T0, "fechamento", Decimal("105"), Decimal("104"))
    ]


def test_aponta_candle_ausente() -> None:
    assert comparar([c1m(0), c1m(1)], [c1m(0)]) == [Divergencia(T0 + M, "ausente", None, None)]
