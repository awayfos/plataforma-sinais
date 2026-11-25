from collections.abc import Callable

import pytest

from sinais.persistencia.memoria import RepositorioCandlesMemoria
from sinais.persistencia.repositorio import RepositorioCandles

from ...contrato.repositorio_candles import CASOS, Fabrica


async def fabrica() -> RepositorioCandles:
    return RepositorioCandlesMemoria()


@pytest.mark.parametrize("caso", CASOS, ids=lambda c: c.__name__)
def test_contrato_memoria(caso: Callable[[Fabrica], None]) -> None:
    caso(fabrica)
