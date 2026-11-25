import pytest

from sinais.persistencia.url import url_async


@pytest.mark.parametrize(
    ("entrada", "saida"),
    [
        ("postgresql://u:p@db/x", "postgresql+asyncpg://u:p@db/x"),
        ("postgres://u:p@db/x", "postgresql+asyncpg://u:p@db/x"),
        ("postgresql+asyncpg://u:p@db/x", "postgresql+asyncpg://u:p@db/x"),
    ],
)
def test_url_async(entrada: str, saida: str) -> None:
    assert url_async(entrada) == saida


def test_url_outro_driver_rejeita() -> None:
    with pytest.raises(ValueError):
        url_async("postgresql+psycopg://u:p@db/x")
