from collections.abc import Callable

import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("alembic")

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from sinais.contas.repositorio import RepositorioContas  # noqa: E402
from sinais.persistencia.consultas_mercado import ConsultasMercado, ConsultasMercadoPg  # noqa: E402
from sinais.persistencia.repositorio import RepositorioCandles  # noqa: E402
from sinais.persistencia.repositorio_contas_pg import RepositorioContasPg  # noqa: E402
from sinais.persistencia.repositorio_pg import RepositorioCandlesPg  # noqa: E402

from ..contrato import consultas_mercado, repositorio_contas  # noqa: E402
from .banco import limpar_contas, migrar  # noqa: E402
from .conftest import exigir_db  # noqa: E402

pytestmark = pytest.mark.integracao


@pytest.fixture(scope="module")
def url() -> str:
    return migrar(exigir_db())


@pytest.mark.parametrize("caso", repositorio_contas.CASOS, ids=lambda c: c.__name__)
def test_contrato_contas_pg(url: str, caso: Callable[[repositorio_contas.Fabrica], None]) -> None:
    async def fabrica() -> RepositorioContas:
        engine = create_async_engine(url)
        await limpar_contas(engine)
        return RepositorioContasPg(engine)

    caso(fabrica)


@pytest.mark.parametrize("caso", consultas_mercado.CASOS, ids=lambda c: c.__name__)
def test_contrato_consultas_pg(
    url: str, caso: Callable[[consultas_mercado.FabricaConsultas], None]
) -> None:
    async def fabrica() -> tuple[RepositorioCandles, ConsultasMercado]:
        engine = create_async_engine(url)
        async with engine.begin() as conn:
            await conn.execute(text("TRUNCATE candles_1m, candles_1s, eventos_qualidade"))
        return RepositorioCandlesPg(engine), ConsultasMercadoPg(engine)

    caso(fabrica)
