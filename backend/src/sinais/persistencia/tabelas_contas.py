"""Tabelas de contas e corretoras (SQLAlchemy Core). A migração 0002 é a fonte da verdade."""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    Time,
)
from sqlalchemy.dialects.postgresql import JSONB

from sinais.persistencia.tabelas import metadados

TS = DateTime(timezone=True)

usuarios = Table(
    "usuarios",
    metadados,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("email", String(254), nullable=False, unique=True),
    Column("nome", String(120), nullable=False),
    Column("papel", String(16), nullable=False),
    Column("status", String(16), nullable=False),
    Column("senha_hash", Text, nullable=False),
    Column("totp_cifrado", Text),
    Column("totp_ultimo_passo", BigInteger),
    Column("criado_em", TS, nullable=False),
)

configuracoes_usuario = Table(
    "configuracoes_usuario",
    metadados,
    Column("usuario_id", BigInteger, ForeignKey("usuarios.id"), primary_key=True),
    Column("modo", String(16), nullable=False),
    Column("layout", JSONB, nullable=False),
    Column("atualizado_em", TS, nullable=False),
)

sessoes = Table(
    "sessoes",
    metadados,
    Column("token_hash", String(64), primary_key=True),
    Column("seq", BigInteger, Identity(), nullable=False),
    Column("csrf_hash", String(64), nullable=False),
    Column("usuario_id", BigInteger, ForeignKey("usuarios.id"), nullable=False),
    Column("criada_em", TS, nullable=False),
    Column("ultimo_uso", TS, nullable=False),
    Column("expira_em", TS, nullable=False),
    Column("ip", String(64), nullable=False),
    Column("user_agent", String(256), nullable=False),
    Column("revogada_em", TS),
    Column("motivo_revogacao", String(32)),
)

planos = Table(
    "planos",
    metadados,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("nome", String(80), nullable=False, unique=True),
    Column("duracao_dias", Integer, nullable=False),
    Column("preco_centavos", Integer, nullable=False),
    Column("recursos", JSONB, nullable=False),
    Column("ativo", Boolean, nullable=False),
)

assinaturas = Table(
    "assinaturas",
    metadados,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("usuario_id", BigInteger, ForeignKey("usuarios.id"), nullable=False),
    Column("plano_id", BigInteger, ForeignKey("planos.id"), nullable=False),
    Column("inicio", TS, nullable=False),
    Column("fim", TS, nullable=False),
    Column("origem", String(16), nullable=False),
    Column("criado_em", TS, nullable=False),
)

registros_acesso = Table(
    "registros_acesso",
    metadados,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("usuario_id", BigInteger, ForeignKey("usuarios.id")),
    Column("evento", String(32), nullable=False),
    Column("ip", String(64), nullable=False),
    Column("user_agent", String(256), nullable=False),
    Column("t", TS, nullable=False),
)

auditoria = Table(
    "auditoria",
    metadados,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("admin_id", BigInteger, ForeignKey("usuarios.id"), nullable=False),
    Column("acao", String(64), nullable=False),
    Column("alvo", String(64), nullable=False),
    Column("antes", JSONB),
    Column("depois", JSONB),
    Column("t", TS, nullable=False),
)

corretoras = Table(
    "corretoras",
    metadados,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("nome", String(64), nullable=False, unique=True),
    Column("notas", Text),
)

corretora_ativos = Table(
    "corretora_ativos",
    metadados,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("corretora_id", BigInteger, ForeignKey("corretoras.id"), nullable=False),
    Column("simbolo", String(32), nullable=False),
    Column("simbolo_corretora", String(64), nullable=False),
    Column("expiracoes_s", JSONB, nullable=False),
    Column("regra_empate", String(32), nullable=False),
)

corretora_payouts = Table(
    "corretora_payouts",
    metadados,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("corretora_ativo_id", BigInteger, ForeignKey("corretora_ativos.id"), nullable=False),
    Column("expiracao_s", Integer, nullable=False),
    Column("hora_inicio", Time),
    Column("hora_fim", Time),
    Column("payout", Numeric(5, 4), nullable=False),
    Column("valido_de", TS, nullable=False),
    Column("valido_ate", TS),
)
