"""Configuração lida de variáveis de ambiente ``SINAIS_*``.

Erros nomeiam a variável e nunca incluem o valor recebido, para não vazar segredos em logs.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, SecretStr, ValidationError


class Ambiente(StrEnum):
    DESENVOLVIMENTO = "dev"
    TESTE = "test"
    PRODUCAO = "prod"


class Configuracao(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    ambiente: Ambiente
    database_url: SecretStr
    redis_url: SecretStr
    nivel_log: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    binance_ws_url: str = "wss://data-stream.binance.vision"
    binance_rest_url: str = "https://api.binance.com"


class ErroConfiguracao(Exception):
    """Configuração ausente ou inválida."""


_VARIAVEIS: dict[str, str] = {campo: f"SINAIS_{campo.upper()}" for campo in Configuracao.model_fields}


def carregar_configuracao(env: Mapping[str, str] | None = None) -> Configuracao:
    fonte = os.environ if env is None else env
    dados = {campo: fonte[var] for campo, var in _VARIAVEIS.items() if var in fonte}
    try:
        return Configuracao.model_validate(dados)
    except ValidationError as erro:
        problemas = []
        for e in erro.errors(include_input=False, include_url=False):
            campo = str(e["loc"][0]) if e["loc"] else "?"
            variavel = _VARIAVEIS.get(campo, campo)
            motivo = "ausente" if e["type"] == "missing" else "valor inválido"
            problemas.append(f"{variavel} ({motivo})")
        raise ErroConfiguracao("configuração inválida: " + ", ".join(problemas)) from None
