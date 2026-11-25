from sinais.dados.qualidade import Lacuna, verificar_sequencia

from .fabrica import M, T0, c1m


def test_sequencia_ok() -> None:
    assert verificar_sequencia([c1m(0), c1m(1), c1m(2)], M).ok


def test_detecta_lacuna() -> None:
    r = verificar_sequencia([c1m(0), c1m(3)], M)
    assert r.lacunas == (Lacuna(T0 + M, T0 + 3 * M),)
    assert not r.ok


def test_detecta_duplicado() -> None:
    r = verificar_sequencia([c1m(0), c1m(1), c1m(1)], M)
    assert r.duplicados == (T0 + M,)


def test_detecta_fora_de_ordem() -> None:
    r = verificar_sequencia([c1m(0), c1m(2), c1m(1)], M)
    assert r.fora_de_ordem == (T0 + M,)


def test_vazio_ok() -> None:
    assert verificar_sequencia([], M).ok
