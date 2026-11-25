from decimal import Decimal

import pytest

from sinais.dados.modelos import Candle, IntervaloColeta

T0 = 1795575600000  # 2026-11-25T03:00:00Z, alinhado a 1m


def candle(**kw: object) -> Candle:
    base: dict[str, object] = {
        "simbolo": "BTCUSDT",
        "intervalo_ms": 60_000,
        "abertura": T0,
        "abertura_preco": Decimal("100"),
        "maxima": Decimal("110"),
        "minima": Decimal("95"),
        "fechamento": Decimal("105"),
        "volume": Decimal("2"),
        "volume_cotacao": Decimal("210"),
        "negocios": 10,
        "volume_compra_agressora": Decimal("1"),
        "fonte": "binance",
    }
    base.update(kw)
    return Candle(**base)  # type: ignore[arg-type]


def test_intervalos() -> None:
    assert IntervaloColeta.S1.duracao_ms == 1000
    assert IntervaloColeta.M1.duracao_ms == 60_000


def test_candle_valido() -> None:
    c = candle()
    assert c.fechamento_ms == T0 + 60_000


@pytest.mark.parametrize(
    "kw",
    [
        {"maxima": Decimal("104")},
        {"minima": Decimal("101")},
        {"abertura": T0 + 1},
        {"volume": Decimal("-1")},
        {"negocios": -1},
    ],
)
def test_candle_invalido_rejeita(kw: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        candle(**kw)
