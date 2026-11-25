"""Conversão da URL de configuração para o driver assíncrono do SQLAlchemy."""

from __future__ import annotations


def url_async(url: str) -> str:
    for prefixo in ("postgresql+asyncpg://", "postgresql://", "postgres://"):
        if url.startswith(prefixo):
            return "postgresql+asyncpg://" + url[len(prefixo) :]
    raise ValueError("URL do banco deve usar postgresql:// ou postgresql+asyncpg://")
