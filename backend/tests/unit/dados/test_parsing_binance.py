import json
from decimal import Decimal

import pytest

from sinais.dados.modelos import IntervaloColeta
from sinais.dados.provedores.binance.parsing import ErroParsing, de_linha_rest, de_mensagem_ws

T0 = 1795575600000
LINHA = [
    T0,
    "0.01634790",
    "0.80000000",
    "0.01575800",
    "0.01577100",
    "148976.11427815",
    T0 + 59_999,
    "2434.19055334",
    308,
    "1756.87402397",
    "28.46694368",
    "0",
]


def kline_ws(fechado: bool) -> dict[str, object]:
    return {
        "e": "kline",
        "E": T0 + 60_001,
        "s": "BTCUSDT",
        "k": {
            "t": T0,
            "T": T0 + 59_999,
            "s": "BTCUSDT",
            "i": "1m",
            "f": 1,
            "L": 2,
            "o": "100.5",
            "c": "101.25",
            "h": "102",
            "l": "99.75",
            "v": "3.5",
            "n": 42,
            "x": fechado,
            "q": "354.0",
            "V": "1.5",
            "Q": "151.0",
            "B": "0",
        },
    }


def test_linha_rest_ok() -> None:
    c = de_linha_rest("BTCUSDT", IntervaloColeta.M1, LINHA)
    assert c.abertura == T0
    assert c.abertura_preco == Decimal("0.01634790")
    assert c.maxima == Decimal("0.80000000")
    assert c.negocios == 308
    assert c.volume_compra_agressora == Decimal("1756.87402397")
    assert c.fonte == "binance"


def test_linha_rest_curta_rejeita() -> None:
    with pytest.raises(ErroParsing):
        de_linha_rest("BTCUSDT", IntervaloColeta.M1, LINHA[:5])


def test_linha_rest_preco_invalido_rejeita() -> None:
    linha = list(LINHA)
    linha[2] = "abc"
    with pytest.raises(ErroParsing) as exc:
        de_linha_rest("BTCUSDT", IntervaloColeta.M1, linha)
    assert "BTCUSDT" in str(exc.value)


def test_ws_envelope_combinado_fechado() -> None:
    texto = json.dumps({"stream": "btcusdt@kline_1m", "data": kline_ws(True)})
    ev = de_mensagem_ws(texto)
    assert ev is not None
    assert ev.fechado is True
    assert ev.candle.fechamento == Decimal("101.25")
    assert ev.candle.intervalo_ms == 60_000
    assert ev.evento_ms == T0 + 60_001


def test_ws_em_formacao_fechado_false() -> None:
    ev = de_mensagem_ws(json.dumps(kline_ws(False)))
    assert ev is not None
    assert ev.fechado is False


def test_ws_evento_nao_kline_devolve_none() -> None:
    assert de_mensagem_ws(json.dumps({"e": "aggTrade", "s": "BTCUSDT"})) is None


def test_ws_json_invalido_rejeita() -> None:
    with pytest.raises(ErroParsing):
        de_mensagem_ws("{nao json")
