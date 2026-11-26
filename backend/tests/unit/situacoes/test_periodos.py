from datetime import UTC, datetime

from sinais.core.tempo import de_datetime
from sinais.situacoes.periodos import periodos_descoberta


def _t(a: int, m: int) -> int:
    return de_datetime(datetime(a, m, 1, tzinfo=UTC))


def test_periodos_da_descoberta_2024_11_a_2026_10() -> None:
    p = periodos_descoberta("2026-10", 24)
    assert (p.inicio, p.fim) == (_t(2024, 11), _t(2026, 11))
    assert len(p.dobras) == 14
    assert p.teste == (_t(2025, 6), _t(2026, 8))
    assert p.holdout == (_t(2026, 8), _t(2026, 11))
    assert p.meses_teste[0] == (_t(2025, 6), _t(2025, 7))
    assert p.calibracao_holdout == (_t(2026, 7), _t(2026, 8))
    assert p.treino_holdout == (_t(2026, 1), _t(2026, 7))
