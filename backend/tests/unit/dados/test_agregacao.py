from decimal import Decimal

from sinais.core.dominio import TempoGrafico
from sinais.dados.modelos import Candle
from sinais.dados.agregacao import AgregadorIncremental, agregar

from .fabrica import M, T0, c1m


def bloco5() -> list[Candle]:
    return [
        c1m(0, o="100", h="101", l="99", c="100.5", v="1"),
        c1m(1, o="100.5", h="103", l="100", c="102", v="2"),
        c1m(2, o="102", h="102.5", l="97", c="98", v="3"),
        c1m(3, o="98", h="99", l="96.5", c="99", v="4"),
        c1m(4, o="99", h="100", l="98", c="99.75", v="5"),
    ]


def test_agrega_5m_completo() -> None:
    [c] = agregar(bloco5(), TempoGrafico.M5)
    assert c.abertura == T0
    assert c.intervalo_ms == 5 * M
    assert (c.abertura_preco, c.maxima, c.minima, c.fechamento) == (
        Decimal("100"), Decimal("103"), Decimal("96.5"), Decimal("99.75"))
    assert c.volume == Decimal("15")
    assert c.negocios == 5
    assert c.fonte == "agregado"


def test_bloco_incompleto_nao_emite() -> None:
    b = bloco5()
    del b[2]
    assert agregar(b, TempoGrafico.M5) == []


def test_agrega_semana_alinhada_segunda() -> None:
    segunda = T0 - 2 * 86_400_000 - 3 * 3_600_000  # 2026-11-23T00:00Z
    minutos = [c1m(i, t0=segunda) for i in range(7 * 24 * 60)]
    [c] = agregar(minutos, TempoGrafico.W1)
    assert c.abertura == segunda


def test_incremental_emite_no_ultimo_minuto() -> None:
    ag = AgregadorIncremental(TempoGrafico.M5)
    saidas = [ag.adicionar(c) for c in bloco5()]
    assert saidas[:4] == [None] * 4
    assert saidas[4] is not None
    assert saidas[4].fechamento == Decimal("99.75")


def test_incremental_descarta_bloco_com_lacuna() -> None:
    ag = AgregadorIncremental(TempoGrafico.M5)
    b = bloco5()
    del b[1]
    assert [ag.adicionar(c) for c in b] == [None] * 4
    proximo = [c1m(i) for i in range(5, 10)]
    assert [ag.adicionar(c) for c in proximo][-1] is not None
