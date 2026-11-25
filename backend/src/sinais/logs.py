"""Logs estruturados: uma linha JSON por evento (ADR-14).

Uso::

    log = obter_logger(__name__)
    log.info("candle.fechado", extra={"campos": {"ativo": "BTCUSDT"}})
"""

from __future__ import annotations

import json
import logging
import math
import sys
import traceback
from typing import Any, TextIO

from sinais.core.tempo import para_iso

_MARCA_HANDLER = "_sinais_json"


class FormatadorJson(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        obj: dict[str, Any] = {
            "ts": para_iso(int(record.created * 1000)),
            "nivel": record.levelname,
            "logger": record.name,
            "evento": record.getMessage(),
        }
        campos = getattr(record, "campos", None)
        if isinstance(campos, dict):
            for chave, valor in campos.items():
                obj[chave if chave not in obj else f"extra_{chave}"] = valor
        if record.exc_info:
            obj["excecao"] = "".join(traceback.format_exception(*record.exc_info))
        return json.dumps(_finitos(obj), ensure_ascii=False, default=str, allow_nan=False)


def _finitos(valor: Any) -> Any:
    """Troca NaN e infinito por ``null``: o JSON estrito não os aceita."""
    if isinstance(valor, float) and not math.isfinite(valor):
        return None
    if isinstance(valor, dict):
        return {k: _finitos(v) for k, v in valor.items()}
    if isinstance(valor, list | tuple):
        return [_finitos(v) for v in valor]
    return valor


def configurar_logs(nivel: str = "INFO", fluxo: TextIO | None = None) -> None:
    """Configura o logger raiz com saída JSON. Chamar de novo substitui o handler anterior."""
    raiz = logging.getLogger()
    for h in [h for h in raiz.handlers if getattr(h, _MARCA_HANDLER, False)]:
        raiz.removeHandler(h)
    handler = logging.StreamHandler(fluxo if fluxo is not None else sys.stdout)
    handler.setFormatter(FormatadorJson())
    setattr(handler, _MARCA_HANDLER, True)
    raiz.addHandler(handler)
    raiz.setLevel(nivel)


def obter_logger(nome: str) -> logging.Logger:
    return logging.getLogger(nome)
