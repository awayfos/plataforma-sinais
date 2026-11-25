"""Preenchimento de histórico pela API REST."""

from __future__ import annotations

from sinais.core.tempo import InstanteMs


def janelas_backfill(
    inicio: InstanteMs, fim: InstanteMs, intervalo_ms: int, limite: int = 1000
) -> list[tuple[InstanteMs, InstanteMs]]:
    """Janelas ``[a, b)`` que cobrem ``[inicio, fim)`` com no máximo ``limite`` candles cada."""
    passo = intervalo_ms * limite
    return [(a, min(a + passo, fim)) for a in range(inicio, fim, passo)]
