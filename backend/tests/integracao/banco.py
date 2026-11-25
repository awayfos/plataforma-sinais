"""Migração e limpeza do banco de integração compartilhadas pelos testes."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from sinais.persistencia.url import url_async

RAIZ = Path(__file__).resolve().parents[2]
TABELAS_CONTAS = (
    "corretora_payouts, auditoria, registros_acesso, pagamentos, assinaturas, planos, "
    "sessoes, configuracoes_usuario, usuarios"
)


def migrar(url_db: str) -> str:
    u = url_async(url_db)
    cfg = Config(str(RAIZ / "alembic.ini"))
    cfg.set_main_option("script_location", str(RAIZ / "migracoes"))
    cfg.attributes["url"] = u
    command.upgrade(cfg, "head")
    return u


async def limpar_contas(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {TABELAS_CONTAS} RESTART IDENTITY CASCADE"))
