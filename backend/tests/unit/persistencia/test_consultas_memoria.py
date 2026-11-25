from collections.abc import Callable

import pytest

from sinais.persistencia.consultas_mercado import ConsultasMercado, ConsultasMercadoMemoria
from sinais.persistencia.memoria import RepositorioCandlesMemoria
from sinais.persistencia.repositorio import RepositorioCandles

from ...contrato.consultas_mercado import CASOS, FabricaConsultas


async def _fabrica() -> tuple[RepositorioCandles, ConsultasMercado]:
    repo = RepositorioCandlesMemoria()
    return repo, ConsultasMercadoMemoria(repo)


@pytest.mark.parametrize("caso", CASOS, ids=lambda c: c.__name__)
def test_contrato_memoria(caso: Callable[[FabricaConsultas], None]) -> None:
    caso(_fabrica)
