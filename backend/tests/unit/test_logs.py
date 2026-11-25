import io
import json
import logging
from collections.abc import Iterator

import pytest

from sinais.logs import configurar_logs, obter_logger


@pytest.fixture
def saida() -> Iterator[io.StringIO]:
    buf = io.StringIO()
    configurar_logs("INFO", buf)
    yield buf
    logging.getLogger().handlers.clear()


def linhas(buf: io.StringIO) -> list[str]:
    return [linha for linha in buf.getvalue().splitlines() if linha]


def test_linha_json_com_campos(saida: io.StringIO) -> None:
    obter_logger("teste").info("candle.fechado", extra={"campos": {"ativo": "BTCUSDT"}})
    [linha] = linhas(saida)
    obj = json.loads(linha)
    assert obj["evento"] == "candle.fechado"
    assert obj["ativo"] == "BTCUSDT"
    assert obj["nivel"] == "INFO"
    assert obj["logger"] == "teste"
    assert obj["ts"].endswith("Z")


def test_excecao_em_campo_unico(saida: io.StringIO) -> None:
    log = obter_logger("teste")
    try:
        1 / 0  # noqa: B018
    except ZeroDivisionError:
        log.exception("falhou")
    [linha] = linhas(saida)
    obj = json.loads(linha)
    assert "ZeroDivisionError" in obj["excecao"]
    assert obj["nivel"] == "ERROR"


def test_idempotente(saida: io.StringIO) -> None:
    configurar_logs("INFO", saida)
    obter_logger("teste").info("uma.vez")
    assert len(linhas(saida)) == 1


def test_nivel_filtra() -> None:
    buf = io.StringIO()
    configurar_logs("WARNING", buf)
    try:
        obter_logger("teste").info("silencio")
        assert buf.getvalue() == ""
    finally:
        logging.getLogger().handlers.clear()


def test_campos_nao_sobrescrevem_chaves_base(saida: io.StringIO) -> None:
    obter_logger("teste").info("evento.real", extra={"campos": {"evento": "falso"}})
    obj = json.loads(linhas(saida)[0])
    assert obj["evento"] == "evento.real"
