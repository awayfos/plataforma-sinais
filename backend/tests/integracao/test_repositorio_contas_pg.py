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


def test_concorrencia_real_no_postgres(url: str) -> None:
    """Logins simultâneos e o mesmo TOTP em paralelo contra o PostgreSQL de verdade."""
    import asyncio

    from sinais.contas.servico import ErroConta

    from ..unit.contas.dubles import T0, admin, ambiente, cliente, codigo_totp

    async def caso() -> None:
        engine = create_async_engine(url)
        await limpar_contas(engine)
        amb = ambiente(repo=RepositorioContasPg(engine))
        u = await cliente(amb)
        await asyncio.gather(
            *(
                amb.servico.login("ana@exemplo.com", "senha-forte-123", None, f"i{i}", "u")
                for i in range(5)
            )
        )
        assert len(await amb.repo.sessoes_ativas(u.id, T0)) == 1
        await admin(amb)
        codigo = codigo_totp(T0)
        resultados = await asyncio.gather(
            *(
                amb.servico.login("admin@exemplo.com", "senha-admin-123", codigo, f"j{i}", "u")
                for i in range(4)
            ),
            return_exceptions=True,
        )
        assert sum(not isinstance(r, ErroConta) for r in resultados) == 1
        await engine.dispose()

    asyncio.run(caso())
