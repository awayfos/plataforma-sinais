"""Tabelas (SQLAlchemy Core). As migrações Alembic são a fonte da verdade do esquema."""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB

metadados = MetaData()
PRECO = Numeric(28, 12)


def _tabela_candles(nome: str) -> Table:
    return Table(
        nome,
        metadados,
        Column("simbolo", String(32), primary_key=True),
        Column("abertura", DateTime(timezone=True), primary_key=True),
        Column("abertura_preco", PRECO, nullable=False),
        Column("maxima", PRECO, nullable=False),
        Column("minima", PRECO, nullable=False),
        Column("fechamento", PRECO, nullable=False),
        Column("volume", PRECO, nullable=False),
        Column("volume_cotacao", PRECO, nullable=False),
        Column("negocios", Integer, nullable=False),
        Column("volume_compra_agressora", PRECO, nullable=False),
        Column("fonte", String(32), nullable=False),
        Column("ingerido_em", DateTime(timezone=True), nullable=False, server_default=func.now()),
    )


candles_1m = _tabela_candles("candles_1m")
candles_1s = _tabela_candles("candles_1s")

eventos_qualidade = Table(
    "eventos_qualidade",
    metadados,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("simbolo", String(32), nullable=False, index=True),
    Column("intervalo", String(8), nullable=False),
    Column("inicio", DateTime(timezone=True), nullable=False),
    Column("fim", DateTime(timezone=True), nullable=False),
    Column("tipo", String(64), nullable=False),
    Column("detalhes", JSONB, nullable=True),
    Column("criado_em", DateTime(timezone=True), nullable=False, server_default=func.now()),
)
