from collections.abc import Callable

import pytest

from sinais.contas.memoria import RepositorioContasMemoria
from sinais.contas.repositorio import RepositorioContas

from ...contrato.repositorio_contas import CASOS, Fabrica


async def _fabrica() -> RepositorioContas:
    return RepositorioContasMemoria()


@pytest.mark.parametrize("caso", CASOS, ids=lambda c: c.__name__)
def test_contrato_memoria(caso: Callable[[Fabrica], None]) -> None:
    caso(_fabrica)
