from datetime import UTC, datetime

import pytest

from sinais.core.dominio import (
    ATIVOS_V1,
    Ativo,
    ClasseAtivo,
    Direcao,
    Expiracao,
    TempoGrafico,
    abertura_candle,
    fechamento_candle,
)
from sinais.core.tempo import de_datetime


def utc(ano: int, mes: int, dia: int, h: int = 0, mi: int = 0, s: int = 0) -> int:
    return de_datetime(datetime(ano, mes, dia, h, mi, s, tzinfo=UTC))


def test_duracoes() -> None:
    assert TempoGrafico.M1.duracao_ms == 60_000
    assert TempoGrafico.H4.duracao_ms == 14_400_000
    assert TempoGrafico.D1.duracao_ms == 86_400_000
    assert TempoGrafico.W1.duracao_ms == 604_800_000


def test_tempos_graficos_da_plataforma() -> None:
    esperado = ["1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"]
    assert [t.value for t in TempoGrafico] == esperado


def test_abertura_na_fronteira_exata() -> None:
    assert abertura_candle(utc(2026, 11, 25, 0, 5), TempoGrafico.M5) == utc(2026, 11, 25, 0, 5)


def test_abertura_um_ms_antes() -> None:
    x = utc(2026, 11, 25, 0, 5) - 1
    assert abertura_candle(x, TempoGrafico.M5) == utc(2026, 11, 25, 0, 0)


def test_semana_comeca_segunda() -> None:
    assert abertura_candle(utc(2026, 11, 25, 12), TempoGrafico.W1) == utc(2026, 11, 23)


def test_domingo_fim_pertence_semana_anterior() -> None:
    assert abertura_candle(utc(2026, 11, 29, 23, 59), TempoGrafico.W1) == utc(2026, 11, 23)


def test_segunda_meia_noite_abre_nova_semana() -> None:
    assert abertura_candle(utc(2026, 11, 30), TempoGrafico.W1) == utc(2026, 11, 30)


def test_fechamento_exclusivo() -> None:
    x = utc(2026, 11, 25, 3, 7, 42)
    assert fechamento_candle(x, TempoGrafico.M1) == abertura_candle(x, TempoGrafico.M1) + 60_000


def test_expiracoes_v1_em_segundos() -> None:
    assert [int(e) for e in Expiracao] == [60, 300, 900, 1800, 3600]


def test_direcao_valores() -> None:
    assert (Direcao.COMPRA, Direcao.VENDA, Direcao.AGUARDAR) == ("BUY", "SELL", "WAIT")


@pytest.mark.parametrize(
    ("simbolo", "precisao"), [("", 2), ("btcusdt", 2), ("BTCUSDT", -1), ("BTCUSDT", 13)]
)
def test_ativo_invalido(simbolo: str, precisao: int) -> None:
    with pytest.raises(ValueError):
        Ativo(simbolo, ClasseAtivo.CRIPTO, "binance", "BTCUSDT", precisao)


def test_ativos_v1() -> None:
    assert tuple(a.simbolo for a in ATIVOS_V1) == ("BTCUSDT", "ETHUSDT")
    assert all(a.classe is ClasseAtivo.CRIPTO for a in ATIVOS_V1)
    assert all(a.provedor == "binance" for a in ATIVOS_V1)


def test_rotulos_de_expiracao_compartilhados() -> None:
    from sinais.core.dominio import EXPIRACAO_POR_ROTULO, ROTULOS_EXPIRACAO, Expiracao

    assert list(ROTULOS_EXPIRACAO.values()) == ["1m", "5m", "15m", "30m", "60m"]
    assert ROTULOS_EXPIRACAO[Expiracao.H1] == "60m"
    assert EXPIRACAO_POR_ROTULO["15m"] is Expiracao.M15 and int(EXPIRACAO_POR_ROTULO["1m"]) == 60
