from datetime import UTC, datetime

import pytest

from sinais.core.calendario import Calendario24x7, CalendarioSemanalFx, calendario_para
from sinais.core.dominio import ATIVOS_V1, Ativo, ClasseAtivo
from sinais.core.tempo import de_datetime


def utc(ano: int, mes: int, dia: int, h: int = 0, mi: int = 0, s: int = 0) -> int:
    return de_datetime(datetime(ano, mes, dia, h, mi, s, tzinfo=UTC))


FX = CalendarioSemanalFx()


def test_cripto_sempre_aberto() -> None:
    cal = calendario_para(ATIVOS_V1[0])
    assert isinstance(cal, Calendario24x7)
    assert cal.aberto(utc(2026, 11, 28, 3)) is True
    assert cal.proxima_abertura(utc(2026, 11, 28, 3)) == utc(2026, 11, 28, 3)


def test_fx_fechado_sabado() -> None:
    assert FX.aberto(utc(2026, 11, 28, 12)) is False


def test_fx_abre_domingo_17h_ny_inverno() -> None:
    assert FX.aberto(utc(2026, 11, 29, 22) - 1) is False
    assert FX.aberto(utc(2026, 11, 29, 22)) is True


def test_fx_abre_domingo_17h_ny_verao() -> None:
    assert FX.aberto(utc(2026, 6, 7, 21) - 1) is False
    assert FX.aberto(utc(2026, 6, 7, 21)) is True


def test_fx_fecha_sexta_17h_ny() -> None:
    assert FX.aberto(utc(2026, 11, 27, 21, 59)) is True
    assert FX.aberto(utc(2026, 11, 27, 22)) is False


def test_fx_aberto_meio_da_semana() -> None:
    assert FX.aberto(utc(2026, 11, 25, 12)) is True


def test_proxima_abertura_fx() -> None:
    assert FX.proxima_abertura(utc(2026, 11, 28, 12)) == utc(2026, 11, 29, 22)


def test_proxima_abertura_fx_quando_aberto() -> None:
    x = utc(2026, 11, 25, 12)
    assert FX.proxima_abertura(x) == x


def test_forex_usa_semanal() -> None:
    eur = Ativo("EURUSD", ClasseAtivo.FOREX, "x", "EURUSD", 5)
    assert isinstance(calendario_para(eur), CalendarioSemanalFx)


def test_acao_nao_implementado() -> None:
    aapl = Ativo("AAPL", ClasseAtivo.ACAO, "x", "AAPL", 2)
    with pytest.raises(NotImplementedError):
        calendario_para(aapl)
