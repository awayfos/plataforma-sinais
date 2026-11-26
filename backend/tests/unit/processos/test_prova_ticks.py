from decimal import Decimal

from sinais.dados.modelos import Candle
from sinais.dados.vela_formacao import Negocio
from sinais.processos.prova_ticks import Kline, comparar, janela_de_gravacao, lacunas_de_id

M = 60_000
T9 = 1795597200000
D_ = Decimal


def c1(abertura: int, o: str, h: str, l: str, c: str, v: str) -> Candle:  # noqa: E741
    return Candle(
        "BTCUSDT", M, abertura, D_(o), D_(h), D_(l), D_(c), D_(v), D_(0), 0, D_(0), "binance"
    )


def test_janela_tem_pelo_menos_3_minutos_e_termina_no_fim_de_um_5m() -> None:
    assert janela_de_gravacao(T9 + 10_000) == (T9 + M, T9 + 5 * M)  # 4 minutos inteiros
    assert janela_de_gravacao(T9 + 3 * M + 1) == (T9 + 4 * M, T9 + 10 * M)  # 1 só não basta


def test_lacunas_de_id() -> None:
    ns = [Negocio(i, D_(1), D_(1), T9, False) for i in (1, 2, 5, 6, 9)]
    assert lacunas_de_id(ns) == [(3, 4), (7, 8)]


def test_comparacao_exata_por_minuto_e_do_5m() -> None:
    negocios = [
        Negocio(1, D_("100.10"), D_("0.5"), T9 + M + 1, False),
        Negocio(2, D_("101"), D_("1.5"), T9 + M + 2, False),
        Negocio(3, D_("99"), D_("1"), T9 + 2 * M, True),
    ]
    antes = [c1(T9, "100", "102", "98", "100.1", "7")]
    k1 = [
        Kline(T9 + M, D_("100.1"), D_("101"), D_("100.1"), D_("101"), D_("2.0")),
        Kline(T9 + 2 * M, D_("99"), D_("99"), D_("99"), D_("99"), D_("1")),
    ]
    k5 = Kline(T9, D_("100"), D_("102"), D_("98"), D_("99"), D_("10"))
    linhas, ok = comparar("BTCUSDT", negocios, antes, k1, k5)
    assert ok and len(linhas) == 3 and all(l.igual for l in linhas)  # noqa: E741
    errado = [Kline(T9 + M, D_("100.1"), D_("101"), D_("100.1"), D_("101"), D_("2.1")), k1[1]]
    _, ok2 = comparar("BTCUSDT", negocios, antes, errado, k5)
    assert not ok2
