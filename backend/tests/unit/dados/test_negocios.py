import json
from decimal import Decimal

import pytest

from sinais.dados.negocios import (
    ErroNegocio,
    canal_ticks,
    de_agg_trade_rest,
    de_agg_trade_ws,
    de_payload,
    para_payload,
)
from sinais.dados.vela_formacao import Negocio

T = 1795597200123


def msg(**data: object) -> str:
    base = {
        "e": "aggTrade",
        "E": T + 5,
        "s": "BTCUSDT",
        "a": 42,
        "p": "58398.01000000",
        "q": "0.00120000",
        "f": 100,
        "l": 101,
        "T": T,
        "m": True,
        "M": True,
    }
    base.update(data)
    return json.dumps({"stream": "btcusdt@aggTrade", "data": base})


def test_ws_aggtrade_vira_negocio_com_decimais_exatos() -> None:
    simbolo, n = de_agg_trade_ws(msg())  # type: ignore[misc]
    assert simbolo == "BTCUSDT"
    assert n == Negocio(42, Decimal("58398.01000000"), Decimal("0.00120000"), T, True)


def test_ws_ignora_outros_eventos_e_recusa_malformados() -> None:
    assert de_agg_trade_ws(json.dumps({"stream": "x", "data": {"e": "kline"}})) is None
    for ruim in (msg(p="abc"), msg(T=-1), msg(a="x"), "lixo", msg(q="-1")):
        with pytest.raises(ErroNegocio):
            de_agg_trade_ws(ruim)


def test_rest_aggtrade() -> None:
    item = {"a": 7, "p": "1.5", "q": "2", "f": 1, "l": 1, "T": T, "m": False, "M": True}
    assert de_agg_trade_rest(item) == Negocio(7, Decimal("1.5"), Decimal("2"), T, False)


def test_payload_do_pubsub_ida_e_volta() -> None:
    n = Negocio(42, Decimal("58398.01"), Decimal("0.0012"), T, True)
    texto = para_payload("BTCUSDT", n)
    assert json.loads(texto) == {
        "versao": "1",
        "simbolo": "BTCUSDT",
        "id": 42,
        "preco": "58398.01",
        "qtd": "0.0012",
        "t": T,
        "maker": True,
    }
    assert de_payload(texto) == ("BTCUSDT", n)
    assert canal_ticks("BTCUSDT") == "ticks:BTCUSDT"
    with pytest.raises(ErroNegocio):
        de_payload('{"simbolo": "BTCUSDT"}')
