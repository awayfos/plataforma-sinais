"""Configuração própria do processo da API (variáveis ``SINAIS_*``).

Erros nomeiam a variável e nunca incluem o valor (a chave de cifra é segredo).
"""

from __future__ import annotations

import base64
import binascii
import os
from collections.abc import Mapping
from ipaddress import IPv4Network, IPv6Network, ip_network
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, field_validator

from sinais.core.config import ErroConfiguracao

# Chave publicada em .env.example: nunca serve fora do desenvolvimento.
CHAVE_DE_EXEMPLO = "ZGVzZW52b2x2aW1lbnRvLW5hby11c2UtZW0tcHJvZCE="
ORIGENS_DESENVOLVIMENTO = ("http://localhost:3000",)


class ConfiguracaoApi(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    ambiente: Literal["dev", "test", "prod"] = "dev"
    chave_cifra: SecretStr
    cookie_seguro: bool = True
    sessoes_simultaneas: int = Field(default=1, ge=1, le=10)
    sessao_horas: int = Field(default=168, ge=1, le=24 * 90)
    sessao_ociosa_horas: int = Field(default=24, ge=1, le=24 * 90)
    registro_modelos: str = "/app/registro"
    ws_verificacao_s: float = Field(default=5.0, gt=0, le=60)
    # None = não definida: no dev vira o frontend local; em prod é obrigatória.
    origens_permitidas: tuple[str, ...] | None = None
    proxies_confiaveis: tuple[IPv4Network | IPv6Network, ...] = ()
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

    @field_validator("proxies_confiaveis", mode="before")
    @classmethod
    def _proxies(cls, v: object) -> object:
        if isinstance(v, str):
            return tuple(ip_network(p.strip(), strict=False) for p in v.split(",") if p.strip())
        return v

    @field_validator("origens_permitidas", mode="before")
    @classmethod
    def _origens(cls, v: object) -> object:
        if isinstance(v, str):
            return tuple(o.strip() for o in v.split(",") if o.strip())
        return v


def _decodificada(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto.encode())


def _exigir_producao(cfg: ConfiguracaoApi) -> None:
    """Recusa em produção o que só serve no desenvolvimento (nunca cita valores)."""

    def recusar(variavel: str, motivo: str) -> None:
        raise ErroConfiguracao(f"configuração inválida: {variavel} ({motivo})")

    # Compara os bytes: a mesma chave escrita de outro jeito também é a de exemplo.
    if _decodificada(cfg.chave_cifra.get_secret_value()) == _decodificada(CHAVE_DE_EXEMPLO):
        recusar("SINAIS_CHAVE_CIFRA", "chave de exemplo em produção")
    if not cfg.origens_permitidas:
        recusar("SINAIS_ORIGENS_PERMITIDAS", "obrigatória em produção")
    elif any(not o.startswith("https://") for o in cfg.origens_permitidas):
        recusar("SINAIS_ORIGENS_PERMITIDAS", "só https:// em produção")
    if not cfg.cookie_seguro:
        recusar("SINAIS_COOKIE_SEGURO", "cookies sem Secure só no desenvolvimento")
    if cfg.documentacao:
        recusar("SINAIS_DOCUMENTACAO", "documentação interativa só no desenvolvimento")


_VARIAVEIS = {campo: f"SINAIS_{campo.upper()}" for campo in ConfiguracaoApi.model_fields}


def carregar_configuracao_api(env: Mapping[str, str] | None = None) -> ConfiguracaoApi:
    fonte = os.environ if env is None else env
    dados = {campo: fonte[var] for campo, var in _VARIAVEIS.items() if var in fonte}
    try:
        cfg = ConfiguracaoApi.model_validate(dados)
    except ValidationError as erro:
        problemas = []
        for e in erro.errors(include_input=False, include_url=False):
            campo = str(e["loc"][0]) if e["loc"] else "?"
            motivo = "ausente" if e["type"] == "missing" else "valor inválido"
            problemas.append(f"{_VARIAVEIS.get(campo, campo)} ({motivo})")
        raise ErroConfiguracao("configuração inválida: " + ", ".join(problemas)) from None
    if cfg.ambiente == "prod":
        _exigir_producao(cfg)
    elif not cfg.origens_permitidas:
        cfg = cfg.model_copy(update={"origens_permitidas": ORIGENS_DESENVOLVIMENTO})
    return cfg
