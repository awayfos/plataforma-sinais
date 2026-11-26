"""Vela em formação a partir de negócios (aggTrade) + candles de 1m oficiais."""

from decimal import Decimal

from sinais.core.dominio import TempoGrafico
from sinais.dados.modelos import Candle
from sinais.dados.vela_formacao import Negocio, VelaEmFormacao

M = 60_000
SEG = 1000
T9 = 1795597200000  # 2026-11-25 (quarta) 09:00:00Z, alinhado a 1h
D = 86_400_000
D_ = Decimal


def neg(id_: int, t: int, preco: str, qtd: str = "1") -> Negocio:
    return Negocio(id=id_, preco=D_(preco), qtd=D_(qtd), t=t, comprador_maker=False)


def oficial(abertura: int, o: str, h: str, l: str, c: str, v: str) -> Candle:  # noqa: E741
    return Candle(
        "BTCUSDT", M, abertura, D_(o), D_(h), D_(l), D_(c), D_(v), D_(0), 0, D_(0), "binance"
    )


def ohlcv(b: VelaEmFormacao, tg: TempoGrafico) -> tuple[int, str, str, str, str, str]:
    v = b.vela(tg)
    assert v is not None
    return (v.t, str(v.o), str(v.h), str(v.l), str(v.c), str(v.v))


def test_negocios_montam_o_minuto_com_o_primeiro_e_o_ultimo_pelo_id() -> None:
    b = VelaEmFormacao("BTCUSDT")
    for n in (neg(1, T9 + 1, "100"), neg(3, T9 + 3 * SEG, "103", "2"), neg(2, T9 + 2 * SEG, "98")):
        assert b.adicionar(n)
    assert ohlcv(b, TempoGrafico.M1) == (T9, "100", "103", "98", "103", "4")
    assert b.ultimo_preco() == (D_("103"), T9 + 3 * SEG)


def test_negocio_exatamente_na_abertura_pertence_ao_novo_minuto() -> None:
    b = VelaEmFormacao("BTCUSDT")
    b.adicionar(neg(1, T9 + M - 1, "100"))
    b.adicionar(neg(2, T9 + M, "101"))
    assert ohlcv(b, TempoGrafico.M1) == (T9 + M, "101", "101", "101", "101", "1")
    assert b.minuto(T9) is not None and str(b.minuto(T9).c) == "100"  # type: ignore[union-attr]
    # em 5m os dois minutos se juntam
    assert ohlcv(b, TempoGrafico.M5) == (T9, "100", "101", "100", "101", "2")


def test_negocio_repetido_ou_fora_de_ordem() -> None:
    b = VelaEmFormacao("BTCUSDT")
    assert b.adicionar(neg(5, T9 + 5 * SEG, "105"))
    assert not b.adicionar(neg(5, T9 + 5 * SEG, "105"))  # repetido (reconexão)
    assert b.adicionar(neg(4, T9 + 4 * SEG, "90"))  # chegou depois, mas é anterior
    assert ohlcv(b, TempoGrafico.M1) == (T9, "90", "105", "90", "105", "2")


def test_fechamento_oficial_substitui_o_parcial_e_descarta_atrasados() -> None:
    b = VelaEmFormacao("BTCUSDT")
    b.carregar([oficial(T9, "100", "110", "95", "105", "10")])
    b.adicionar(neg(10, T9 + M + 1, "106"))
    b.adicionar(neg(11, T9 + 2 * M + 1, "107"))  # já é do minuto seguinte
    # o oficial do minuto T9+M difere do parcial (faltou um negócio): vale o oficial
    assert b.fechar_1m(oficial(T9 + M, "106", "109", "104", "108", "3"))
    assert ohlcv(b, TempoGrafico.M5) == (T9, "100", "110", "95", "107", "14")
    assert ohlcv(b, TempoGrafico.M1) == (T9 + 2 * M, "107", "107", "107", "107", "1")
    assert not b.adicionar(neg(9, T9 + M + 30 * SEG, "1"))  # do minuto já fechado
    assert not b.precisa_recarregar


def test_lacuna_de_fechamentos_pede_recarga() -> None:
    b = VelaEmFormacao("BTCUSDT")
    b.carregar([oficial(T9, "100", "110", "95", "105", "10")])
    b.fechar_1m(oficial(T9 + 2 * M, "1", "1", "1", "1", "1"))  # faltou o de T9+M
    assert b.precisa_recarregar
    b.carregar(
        [
            oficial(T9, "100", "110", "95", "105", "10"),
            oficial(T9 + M, "105", "106", "104", "106", "1"),
            oficial(T9 + 2 * M, "106", "107", "100", "101", "2"),
        ]
    )
    assert not b.precisa_recarregar
    b.adicionar(neg(1, T9 + 3 * M, "102"))
    assert ohlcv(b, TempoGrafico.M5) == (T9, "100", "110", "95", "102", "14")


def test_ressincronizacao_por_rest_nao_duplica() -> None:
    b = VelaEmFormacao("BTCUSDT")
    ao_vivo = [neg(i, T9 + i * SEG, str(100 + i)) for i in range(1, 6)]
    for n in ao_vivo[:3]:
        b.adicionar(n)
    # reconexão: o REST devolve tudo desde a abertura do minuto, inclusive o que já veio
    for n in ao_vivo:
        b.adicionar(n)
    assert ohlcv(b, TempoGrafico.M1) == (T9, "101", "105", "101", "105", "5")


def test_virada_da_semana_comeca_na_segunda() -> None:
    domingo = 1795996800000 - M  # 2026-11-29 (domingo) 23:59:00Z; segunda 00:00 = 1795996800000
    segunda = domingo + M
    b = VelaEmFormacao("BTCUSDT")
    b.carregar([oficial(domingo - M, "50", "60", "40", "55", "1")])
    b.adicionar(neg(1, domingo + SEG, "56"))
    assert ohlcv(b, TempoGrafico.W1)[0] == segunda - 7 * D
    assert ohlcv(b, TempoGrafico.W1)[1] == "50"  # a semana inclui o oficial anterior
    b.adicionar(neg(2, segunda + SEG, "57"))
    assert ohlcv(b, TempoGrafico.W1) == (segunda, "57", "57", "57", "57", "1")
    assert ohlcv(b, TempoGrafico.D1) == (segunda, "57", "57", "57", "57", "1")


def test_sem_negocios_nao_ha_vela() -> None:
    b = VelaEmFormacao("BTCUSDT")
    assert b.vela(TempoGrafico.M1) is None and b.ultimo_preco() is None
