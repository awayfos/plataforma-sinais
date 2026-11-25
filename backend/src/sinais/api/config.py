"""Configuração própria do processo da API (variáveis ``SINAIS_*``).

Erros nomeiam a variável e nunca incluem o valor (a chave de cifra é segredo).
"""

from __future__ import annotations

import base64
import binascii
import os
from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, field_validator

from sinais.core.config import ErroConfiguracao


class ConfiguracaoApi(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    chave_cifra: SecretStr
    cookie_seguro: bool = True
    sessoes_simultaneas: int = Field(default=1, ge=1, le=10)
    sessao_horas: int = Field(default=168, ge=1, le=24 * 90)
    sessao_ociosa_horas: int = Field(default=24, ge=1, le=24 * 90)
    registro_modelos: str = "/app/registro"
    ws_verificacao_s: float = Field(default=5.0, gt=0, le=60)
    origens_permitidas: tuple[str, ...] = ()
    confiar_proxy: bool = False
    documentacao: bool = False

    @field_validator("chave_cifra")
    @classmethod
    def _chave(cls, v: SecretStr) -> SecretStr:
        try:
            bruto = base64.urlsafe_b64decode(v.get_secret_value().encode())
        except (binascii.Error, ValueError):
            raise ValueError("base64 inválido") from None
        if len(bruto) != 32:
            raise ValueError("a chave deve ter 32 bytes")
        return v

    @field_validator("origens_permitidas", mode="before")
    @classmethod
    def _origens(cls, v: object) -> object:
        if isinstance(v, str):
            return tuple(o.strip() for o in v.split(",") if o.strip())
        return v


_VARIAVEIS = {campo: f"SINAIS_{campo.upper()}" for campo in ConfiguracaoApi.model_fields}


def carregar_configuracao_api(env: Mapping[str, str] | None = None) -> ConfiguracaoApi:
    fonte = os.environ if env is None else env
    dados = {campo: fonte[var] for campo, var in _VARIAVEIS.items() if var in fonte}
    try:
        return ConfiguracaoApi.model_validate(dados)
    except ValidationError as erro:
        problemas = []
        for e in erro.errors(include_input=False, include_url=False):
            campo = str(e["loc"][0]) if e["loc"] else "?"
            motivo = "ausente" if e["type"] == "missing" else "valor inválido"
            problemas.append(f"{_VARIAVEIS.get(campo, campo)} ({motivo})")
        raise ErroConfiguracao("configuração inválida: " + ", ".join(problemas)) from None
