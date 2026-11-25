import asyncio
from collections.abc import Callable
from pathlib import Path

import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("alembic")

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from sinais.persistencia.repositorio import RepositorioCandles  # noqa: E402
from sinais.persistencia.repositorio_pg import RepositorioCandlesPg  # noqa: E402
from sinais.persistencia.url import url_async  # noqa: E402

from ..contrato.repositorio_candles import CASOS, Fabrica  # noqa: E402
from .conftest import exigir_db  # noqa: E402

pytestmark = pytest.mark.integracao
RAIZ = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def url() -> str:
    u = url_async(exigir_db())
    cfg = Config(str(RAIZ / "alembic.ini"))
    cfg.set_main_option("script_location", str(RAIZ / "migracoes"))
    cfg.attributes["url"] = u
    command.upgrade(cfg, "head")
    return u


def fabrica_para(url: str) -> Fabrica:
    async def fabrica() -> RepositorioCandles:
        engine = create_async_engine(url)
        async with engine.begin() as conn:
            await conn.execute(text("TRUNCATE candles_1m, candles_1s, eventos_qualidade"))
        return RepositorioCandlesPg(engine)

    return fabrica


@pytest.mark.parametrize("caso", CASOS, ids=lambda c: c.__name__)
def test_contrato_pg(url: str, caso: Callable[[Fabrica], None]) -> None:
    caso(fabrica_para(url))


def test_migracao_cria_hypertables(url: str) -> None:
    async def caso() -> set[str]:
        engine = create_async_engine(url)
        async with engine.connect() as conn:
            linhas = await conn.execute(
                text("SELECT hypertable_name FROM timescaledb_information.hypertables")
            )
            nomes = {r[0] for r in linhas}
        await engine.dispose()
        return nomes

    assert {"candles_1m", "candles_1s"} <= asyncio.run(caso())
