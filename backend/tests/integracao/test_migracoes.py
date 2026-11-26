"""A migração 0002 desce e sobe limpa, e as restrições do esquema valem no banco real."""

import asyncio

import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("alembic")

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from .banco import RAIZ, limpar_contas, migrar  # noqa: E402
from .conftest import exigir_db  # noqa: E402

pytestmark = pytest.mark.integracao


def _tabelas(url: str) -> set[str]:
    async def ler() -> set[str]:
        engine = create_async_engine(url)
        async with engine.connect() as conn:
            linhas = await conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            )
            nomes = {r[0] for r in linhas}
        await engine.dispose()
        return nomes

    return asyncio.run(ler())


def test_downgrade_para_0001_e_upgrade_de_novo() -> None:
    url = migrar(exigir_db())
    cfg = Config(str(RAIZ / "alembic.ini"))
    cfg.set_main_option("script_location", str(RAIZ / "migracoes"))
    cfg.attributes["url"] = url
    assert {"usuarios", "sessoes", "corretora_payouts"} <= _tabelas(url)
    command.downgrade(cfg, "0001")
    restantes = _tabelas(url)
    assert "usuarios" not in restantes and "corretora_payouts" not in restantes
    assert {"candles_1m", "candles_1s", "eventos_qualidade"} <= restantes
    command.upgrade(cfg, "head")
    assert {"usuarios", "sessoes", "corretora_payouts"} <= _tabelas(url)


def test_um_payout_vigente_por_ativo_e_expiracao_e_expiracao_valida() -> None:
    url = migrar(exigir_db())

    async def caso() -> None:
        engine = create_async_engine(url)
        await limpar_contas(engine)
        inserir = text(
            "INSERT INTO corretora_payouts (corretora_ativo_id, expiracao_s, payout, valido_de) "
            "SELECT id, :e, 0.88, now() FROM corretora_ativos WHERE simbolo = 'BTCUSDT'"
        )
        async with engine.begin() as conn:
            await conn.execute(inserir, {"e": 60})
        with pytest.raises(IntegrityError):
            async with engine.begin() as conn:
                await conn.execute(inserir, {"e": 60})
        with pytest.raises(IntegrityError):
            async with engine.begin() as conn:
                await conn.execute(inserir, {"e": 120})
        await limpar_contas(engine)
        await engine.dispose()

    asyncio.run(caso())
