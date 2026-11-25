"""Preenchimento de histórico pela API REST."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol

from sinais.core.tempo import InstanteMs
from sinais.dados.modelos import Candle, IntervaloColeta
from sinais.dados.qualidade import Lacuna
from sinais.logs import obter_logger
from sinais.persistencia.repositorio import RepositorioCandles

_log = obter_logger(__name__)


def janelas_backfill(
    inicio: InstanteMs, fim: InstanteMs, intervalo_ms: int, limite: int = 1000
) -> list[tuple[InstanteMs, InstanteMs]]:
    """Janelas ``[a, b)`` que cobrem ``[inicio, fim)`` com no máximo ``limite`` candles cada."""
    passo = intervalo_ms * limite
    return [(a, min(a + passo, fim)) for a in range(inicio, fim, passo)]


class FonteHistorico(Protocol):
    async def klines(
        self,
        simbolo: str,
        intervalo: IntervaloColeta,
        inicio: InstanteMs,
        fim: InstanteMs,
        limite: int = 1000,
    ) -> list[Candle]: ...


async def preencher(
    fonte: FonteHistorico,
    repo: RepositorioCandles,
    simbolo: str,
    intervalo: IntervaloColeta,
    inicio: InstanteMs,
    fim: InstanteMs,
    ao_gravar: Callable[[list[Candle]], Awaitable[None]] | None = None,
) -> int:
    """Baixa ``[inicio, fim)`` em janelas, grava e registra as lacunas que a fonte não cobriu."""
    dur = intervalo.duracao_ms
    gravados = 0
    esperado = inicio
    for a, b in janelas_backfill(inicio, fim, dur):
        candles = sorted(await fonte.klines(simbolo, intervalo, a, b), key=lambda c: c.abertura)
        candles = [c for c in candles if a <= c.abertura < b]
        gravados += await repo.inserir(candles)
        if ao_gravar is not None and candles:
            await ao_gravar(candles)
        for c in candles:
            if c.abertura > esperado:
                await _lacuna(repo, simbolo, intervalo, Lacuna(esperado, c.abertura))
            esperado = max(esperado, c.abertura + dur)
    if esperado < fim:
        await _lacuna(repo, simbolo, intervalo, Lacuna(esperado, fim))
    _log.info(
        "backfill.concluido",
        extra={"campos": {"simbolo": simbolo, "intervalo": intervalo.value, "gravados": gravados}},
    )
    return gravados


async def _lacuna(
    repo: RepositorioCandles, simbolo: str, intervalo: IntervaloColeta, lacuna: Lacuna
) -> None:
    await repo.registrar_qualidade(simbolo, intervalo, lacuna, "lacuna_rest")
    _log.warning(
        "backfill.lacuna",
        extra={
            "campos": {
                "simbolo": simbolo,
                "intervalo": intervalo.value,
                "inicio": lacuna.inicio,
                "fim": lacuna.fim,
            }
        },
    )
