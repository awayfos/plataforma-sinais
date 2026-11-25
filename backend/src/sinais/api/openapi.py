"""Gera o snapshot do OpenAPI do contrato v1.

Uso: ``python -m sinais.api.openapi > docs/api/openapi-v1.json``.
"""

from __future__ import annotations

import json
from typing import Any, cast


def esquema_openapi() -> dict[str, Any]:
    from fastapi.openapi.utils import get_openapi

    from sinais.api.app import VERSAO_API, criar_app
    from sinais.api.servicos import Servicos

    # O esquema só depende das rotas: os serviços nunca são chamados aqui.
    nada = cast(Any, None)
    app = criar_app(
        Servicos(contas=nada, admin=nada, mercado=nada, analises=nada, campeao=lambda s, e: None)
    )
    esquema: dict[str, Any] = get_openapi(
        title=app.title, version=VERSAO_API, routes=app.routes, description=app.description
    )
    return esquema


def texto_openapi() -> str:
    return json.dumps(esquema_openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


if __name__ == "__main__":  # pragma: no cover
    print(texto_openapi(), end="")
