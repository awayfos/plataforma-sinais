from sinais.dados.backfill import janelas_backfill

from .fabrica import M, T0


def test_janelas_exatas() -> None:
    js = janelas_backfill(T0, T0 + 2500 * M, M)
    assert js == [(T0, T0 + 1000 * M), (T0 + 1000 * M, T0 + 2000 * M), (T0 + 2000 * M, T0 + 2500 * M)]


def test_janelas_vazio_quando_inicio_igual_fim() -> None:
    assert janelas_backfill(T0, T0, M) == []
