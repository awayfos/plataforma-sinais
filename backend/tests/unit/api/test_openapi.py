"""O snapshot ``docs/api/openapi-v1.json`` acompanha o código e cobre todas as rotas do contrato."""

import json
import os
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from sinais.api.openapi import esquema_openapi, texto_openapi  # noqa: E402

SNAPSHOT = Path(__file__).resolve().parents[4] / "docs" / "api" / "openapi-v1.json"
ROTAS_DO_CONTRATO = {
    ("post", "/api/auth/login"),
    ("post", "/api/auth/logout"),
    ("get", "/api/eu"),
    ("post", "/api/eu/senha"),
    ("patch", "/api/eu/preferencias"),
    ("get", "/api/ativos"),
    ("get", "/api/candles"),
    ("get", "/api/analise"),
    ("get", "/api/sinais"),
    ("get", "/api/sinais/historico"),
    ("get", "/api/admin/usuarios"),
    ("post", "/api/admin/usuarios"),
    ("patch", "/api/admin/usuarios/{usuario_id}"),
    ("get", "/api/admin/planos"),
    ("post", "/api/admin/planos"),
    ("patch", "/api/admin/planos/{plano_id}"),
    ("post", "/api/admin/assinaturas"),
    ("get", "/api/admin/acessos"),
    ("get", "/api/admin/auditoria"),
    ("get", "/api/admin/corretoras/exnova/payout"),
    ("put", "/api/admin/corretoras/exnova/payout"),
    ("get", "/api/admin/qualidade"),
    ("get", "/api/publico/estatisticas"),
}


def test_todas_as_rotas_do_contrato_existem() -> None:
    caminhos = esquema_openapi()["paths"]
    existentes = {(m, p) for p, ops in caminhos.items() for m in ops}
    assert ROTAS_DO_CONTRATO <= existentes, ROTAS_DO_CONTRATO - existentes


def test_snapshot_atualizado() -> None:
    atual = texto_openapi()
    if os.environ.get("SINAIS_ATUALIZAR_OPENAPI") == "1":
        SNAPSHOT.write_text(atual)
    assert SNAPSHOT.exists(), "gere com: python -m sinais.api.openapi > docs/api/openapi-v1.json"
    assert json.loads(SNAPSHOT.read_text()) == json.loads(atual), (
        "OpenAPI mudou: regenere docs/api/openapi-v1.json com python -m sinais.api.openapi"
    )
