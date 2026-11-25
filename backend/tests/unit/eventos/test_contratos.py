import asyncio
from decimal import Decimal

from sinais.dados.modelos import Candle
from sinais.eventos.contratos import STREAM_CANDLE_FECHADO, evento_candle_fechado
from sinais.eventos.memoria import PublicadorMemoria

T0 = 1795575600000


def vela() -> Candle:
    return Candle(
        "BTCUSDT",
        60_000,
        T0,
        Decimal("59194.01"),
        Decimal("59200.5"),
        Decimal("59190"),
        Decimal("59199.99"),
        Decimal("1.23456789"),
        Decimal("73080.12"),
        42,
        Decimal("0.5"),
        "binance",
    )


def test_evento_campos_e_id() -> None:
    ev = evento_candle_fechado(vela())
    assert ev["versao"] == "1"
    assert ev["id"] == f"BTCUSDT:60000:{T0}"
    assert ev["simbolo"] == "BTCUSDT"
    assert ev["intervalo_ms"] == "60000"
    assert ev["abertura"] == str(T0)
    assert ev["fonte"] == "binance"
    assert all(isinstance(v, str) for v in ev.values())


def test_decimal_preservado_como_string() -> None:
    ev = evento_candle_fechado(vela())
    assert (ev["o"], ev["h"], ev["l"], ev["c"], ev["v"]) == (
        "59194.01",
        "59200.5",
        "59190",
        "59199.99",
        "1.23456789",
    )


def test_publicador_memoria_guarda_por_stream() -> None:
    p = PublicadorMemoria()
    asyncio.run(p.publicar(STREAM_CANDLE_FECHADO, {"a": "1"}))
    assert p.publicados == [(STREAM_CANDLE_FECHADO, {"a": "1"})]
