import asyncio

from sinais.dados.backfill import preencher
from sinais.dados.modelos import IntervaloColeta
from sinais.persistencia.memoria import RepositorioCandlesMemoria

from .fonte_falsa import FonteFalsa

T0 = 1795575600000
M = 60_000


def test_preencher_grava_todas_as_janelas() -> None:
    fonte, repo = FonteFalsa(), RepositorioCandlesMemoria()
    n = asyncio.run(preencher(fonte, repo, "BTCUSDT", IntervaloColeta.M1, T0, T0 + 2500 * M))
    assert n == 2500
    assert len(fonte.chamadas) == 3
    assert asyncio.run(repo.ultima_abertura("BTCUSDT", IntervaloColeta.M1)) == T0 + 2499 * M


def test_preencher_registra_lacuna_restante() -> None:
    fonte = FonteFalsa(faltando={T0 + 2 * M, T0 + 3 * M, T0 + 9 * M})
    repo = RepositorioCandlesMemoria()
    asyncio.run(preencher(fonte, repo, "BTCUSDT", IntervaloColeta.M1, T0, T0 + 10 * M))
    eventos = asyncio.run(repo.eventos_qualidade("BTCUSDT"))
    assert eventos == [
        ("BTCUSDT", "1m", T0 + 2 * M, T0 + 4 * M, "lacuna_rest"),
        ("BTCUSDT", "1m", T0 + 9 * M, T0 + 10 * M, "lacuna_rest"),
    ]


def test_preencher_chama_ao_gravar_com_candles_novos() -> None:
    fonte, repo = FonteFalsa(), RepositorioCandlesMemoria()
    vistos: list[int] = []

    async def ao_gravar(cs: list) -> None:  # type: ignore[type-arg]
        vistos.extend(c.abertura for c in cs)

    asyncio.run(
        preencher(fonte, repo, "BTCUSDT", IntervaloColeta.M1, T0, T0 + 3 * M, ao_gravar=ao_gravar)
    )
    assert vistos == [T0, T0 + M, T0 + 2 * M]
