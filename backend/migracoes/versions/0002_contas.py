"""Contas e comercial (design §11): usuários, sessões, planos, assinaturas, pagamentos,
logs de acesso, auditoria, configurações do usuário e payout por corretora.

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

TS = sa.DateTime(timezone=True)


def _agora() -> sa.Column:
    return sa.Column("criado_em", TS, nullable=False, server_default=sa.func.now())


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("papel", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="ativo"),
        sa.Column("senha_hash", sa.Text, nullable=False),
        sa.Column("totp_cifrado", sa.Text, nullable=True),
        sa.Column("totp_ultimo_passo", sa.BigInteger, nullable=True),
        sa.Column("criado_em", TS, nullable=False),
        sa.CheckConstraint("papel IN ('cliente', 'admin')", name="ck_usuarios_papel"),
        sa.CheckConstraint(
            "status IN ('ativo', 'bloqueado', 'desativado')", name="ck_usuarios_status"
        ),
        sa.CheckConstraint("email = lower(email)", name="ck_usuarios_email_minusculo"),
    )
    op.create_table(
        "configuracoes_usuario",
        sa.Column(
            "usuario_id",
            sa.BigInteger,
            sa.ForeignKey("usuarios.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("modo", sa.String(16), nullable=False, server_default="essencial"),
        sa.Column("layout", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("atualizado_em", TS, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("modo IN ('essencial', 'avancado')", name="ck_config_modo"),
    )
    op.create_table(
        "sessoes",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("csrf_hash", sa.String(64), nullable=False),
        sa.Column(
            "usuario_id",
            sa.BigInteger,
            sa.ForeignKey("usuarios.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("criada_em", TS, nullable=False),
        sa.Column("ultimo_uso", TS, nullable=False),
        sa.Column("expira_em", TS, nullable=False),
        sa.Column("ip", sa.String(64), nullable=False),
        sa.Column("user_agent", sa.String(256), nullable=False),
        sa.Column("revogada_em", TS, nullable=True),
        sa.Column("motivo_revogacao", sa.String(32), nullable=True),
    )
    op.create_table(
        "planos",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("nome", sa.String(80), nullable=False, unique=True),
        sa.Column("duracao_dias", sa.Integer, nullable=False),
        sa.Column("preco_centavos", sa.Integer, nullable=False),
        sa.Column("recursos", JSONB, nullable=False),
        sa.Column("ativo", sa.Boolean, nullable=False, server_default=sa.true()),
        _agora(),
        sa.CheckConstraint("duracao_dias > 0", name="ck_planos_duracao"),
        sa.CheckConstraint("preco_centavos >= 0", name="ck_planos_preco"),
    )
    op.create_table(
        "assinaturas",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column(
            "usuario_id",
            sa.BigInteger,
            sa.ForeignKey("usuarios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("plano_id", sa.BigInteger, sa.ForeignKey("planos.id"), nullable=False),
        sa.Column("inicio", TS, nullable=False),
        sa.Column("fim", TS, nullable=False),
        sa.Column("origem", sa.String(16), nullable=False, server_default="manual"),
        sa.Column("criado_em", TS, nullable=False),
        sa.CheckConstraint("fim > inicio", name="ck_assinaturas_periodo"),
    )
    op.create_index("ix_assinaturas_usuario_fim", "assinaturas", ["usuario_id", "fim"])
    op.create_table(
        "pagamentos",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("assinatura_id", sa.BigInteger, sa.ForeignKey("assinaturas.id"), nullable=False),
        sa.Column("valor_centavos", sa.Integer, nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("referencia_externa", sa.String(128), nullable=True),
        _agora(),
    )
    op.create_table(
        "registros_acesso",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column(
            "usuario_id",
            sa.BigInteger,
            sa.ForeignKey("usuarios.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("evento", sa.String(32), nullable=False),
        sa.Column("ip", sa.String(64), nullable=False),
        sa.Column("user_agent", sa.String(256), nullable=False),
        sa.Column("t", TS, nullable=False),
    )
    op.create_index("ix_registros_acesso_usuario_t", "registros_acesso", ["usuario_id", "t"])
    op.create_index("ix_registros_acesso_t", "registros_acesso", ["t"])
    op.create_table(
        "auditoria",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("admin_id", sa.BigInteger, sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("acao", sa.String(64), nullable=False),
        sa.Column("alvo", sa.String(64), nullable=False),
        sa.Column("antes", JSONB, nullable=True),
        sa.Column("depois", JSONB, nullable=True),
        sa.Column("t", TS, nullable=False, index=True),
    )
    op.create_table(
        "corretoras",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("nome", sa.String(64), nullable=False, unique=True),
        sa.Column("notas", sa.Text, nullable=True),
    )
    op.create_table(
        "corretora_ativos",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("corretora_id", sa.BigInteger, sa.ForeignKey("corretoras.id"), nullable=False),
        sa.Column("simbolo", sa.String(32), nullable=False),
        sa.Column("simbolo_corretora", sa.String(64), nullable=False),
        sa.Column("expiracoes_s", JSONB, nullable=False),
        sa.Column("regra_empate", sa.String(32), nullable=False, server_default="devolve"),
        sa.UniqueConstraint("corretora_id", "simbolo", name="uq_corretora_ativo"),
    )
    # Payout com dimensão de expiração e faixa horária opcional desde o início (design §11).
    op.create_table(
        "corretora_payouts",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column(
            "corretora_ativo_id",
            sa.BigInteger,
            sa.ForeignKey("corretora_ativos.id"),
            nullable=False,
        ),
        sa.Column("expiracao_s", sa.Integer, nullable=False),
        sa.Column("hora_inicio", sa.Time, nullable=True),
        sa.Column("hora_fim", sa.Time, nullable=True),
        sa.Column("payout", sa.Numeric(5, 4), nullable=False),
        sa.Column("valido_de", TS, nullable=False),
        sa.Column("valido_ate", TS, nullable=True),
        sa.CheckConstraint("payout > 0 AND payout <= 1", name="ck_payout_faixa"),
    )
    op.create_index(
        "ix_corretora_payouts_vigencia",
        "corretora_payouts",
        ["corretora_ativo_id", "expiracao_s", "valido_de"],
    )
    op.execute("INSERT INTO corretoras (nome, notas) VALUES ('exnova', 'Plataforma Quadcode')")
    op.execute(
        "INSERT INTO corretora_ativos (corretora_id, simbolo, simbolo_corretora, expiracoes_s) "
        "SELECT id, s.simbolo, s.simbolo_corretora, '[60, 300, 900, 1800, 3600]'::jsonb "
        "FROM corretoras, (VALUES ('BTCUSDT', 'BTC/USDT'), ('ETHUSDT', 'ETH/USDT')) "
        "AS s(simbolo, simbolo_corretora) WHERE corretoras.nome = 'exnova'"
    )


def downgrade() -> None:
    for tabela in (
        "corretora_payouts",
        "corretora_ativos",
        "corretoras",
        "auditoria",
        "registros_acesso",
        "pagamentos",
        "assinaturas",
        "planos",
        "sessoes",
        "configuracoes_usuario",
        "usuarios",
    ):
        op.drop_table(tabela)
