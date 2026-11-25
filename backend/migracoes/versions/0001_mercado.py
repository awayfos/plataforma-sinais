"""Tabelas de mercado: candles de 1 s e 1 min (hypertables) e eventos de qualidade.

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

PRECO = sa.Numeric(28, 12)


def _candles(nome: str) -> None:
    op.create_table(
        nome,
        sa.Column("simbolo", sa.String(32), primary_key=True),
        sa.Column("abertura", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("abertura_preco", PRECO, nullable=False),
        sa.Column("maxima", PRECO, nullable=False),
        sa.Column("minima", PRECO, nullable=False),
        sa.Column("fechamento", PRECO, nullable=False),
        sa.Column("volume", PRECO, nullable=False),
        sa.Column("volume_cotacao", PRECO, nullable=False),
        sa.Column("negocios", sa.Integer, nullable=False),
        sa.Column("volume_compra_agressora", PRECO, nullable=False),
        sa.Column("fonte", sa.String(32), nullable=False),
        sa.Column(
            "ingerido_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.execute(
        f"SELECT create_hypertable('{nome}', 'abertura', "
        "chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE)"
    )


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
    _candles("candles_1m")
    _candles("candles_1s")
    op.create_table(
        "eventos_qualidade",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("simbolo", sa.String(32), nullable=False, index=True),
        sa.Column("intervalo", sa.String(8), nullable=False),
        sa.Column("inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fim", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tipo", sa.String(64), nullable=False),
        sa.Column("detalhes", JSONB, nullable=True),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    op.drop_table("eventos_qualidade")
    op.drop_table("candles_1s")
    op.drop_table("candles_1m")
