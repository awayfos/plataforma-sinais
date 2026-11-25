"""Integração com PostgreSQL/TimescaleDB e Redis reais (CI). Pulado sem as variáveis."""

import os

import pytest

URL_DB = os.environ.get("SINAIS_TESTE_DATABASE_URL")
URL_REDIS = os.environ.get("SINAIS_TESTE_REDIS_URL")

pytestmark = pytest.mark.integracao


def exigir_db() -> str:
    if not URL_DB:
        pytest.skip("SINAIS_TESTE_DATABASE_URL não definida")
    return URL_DB


def exigir_redis() -> str:
    if not URL_REDIS:
        pytest.skip("SINAIS_TESTE_REDIS_URL não definida")
    return URL_REDIS
