"""Ambiente do Alembic: usa SINAIS_DATABASE_URL e o driver asyncpg."""

import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from sinais.core.config import carregar_configuracao
from sinais.persistencia.tabelas import metadados
from sinais.persistencia.url import url_async


def _executar(conexao) -> None:  # type: ignore[no-untyped-def]
    context.configure(connection=conexao, target_metadata=metadados)
    with context.begin_transaction():
        context.run_migrations()


async def _online() -> None:
    url = context.config.attributes.get("url") or url_async(
        carregar_configuracao().database_url.get_secret_value()
    )
    engine = create_async_engine(url)
    async with engine.connect() as conexao:
        await conexao.run_sync(_executar)
    await engine.dispose()


asyncio.run(_online())
