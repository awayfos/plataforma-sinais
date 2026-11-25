import time
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from sinais.core.tempo import (
    RelogioFixo,
    RelogioSistema,
    de_datetime,
    para_datetime,
    para_iso,
    validar_instante,
)

QUARTA_03H_UTC = 1795575600000  # 2026-11-25T03:00:00Z


def test_de_datetime_utc() -> None:
    assert de_datetime(datetime(2026, 11, 25, 3, 0, tzinfo=UTC)) == QUARTA_03H_UTC


def test_de_datetime_com_fuso_converte() -> None:
    sp = datetime(2026, 11, 25, 0, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    assert de_datetime(sp) == QUARTA_03H_UTC


def test_de_datetime_ingenuo_rejeita() -> None:
    with pytest.raises(ValueError):
        de_datetime(datetime(2026, 11, 25, 3, 0))


def test_para_iso() -> None:
    assert para_iso(QUARTA_03H_UTC + 123) == "2026-11-25T03:00:00.123Z"


@pytest.mark.parametrize("x", [0, 1, QUARTA_03H_UTC + 123])
def test_ida_e_volta(x: int) -> None:
    assert de_datetime(para_datetime(x)) == x


@pytest.mark.parametrize("valor", [-1, 1.5, True, "10"])
def test_validar_instante_rejeita(valor: object) -> None:
    with pytest.raises(ValueError):
        validar_instante(valor)


def test_validar_instante_aceita_inteiro() -> None:
    assert validar_instante(42) == 42


def test_relogio_fixo_avanca() -> None:
    r = RelogioFixo(1000)
    r.avancar(500)
    assert r.agora_ms() == 1500


def test_relogio_fixo_definir() -> None:
    r = RelogioFixo(1000)
    r.definir(QUARTA_03H_UTC)
    assert r.agora_ms() == QUARTA_03H_UTC


def test_relogio_sistema_proximo_de_time() -> None:
    assert abs(RelogioSistema().agora_ms() - int(time.time() * 1000)) < 1000
