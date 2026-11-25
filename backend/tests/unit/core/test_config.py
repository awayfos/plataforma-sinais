import pytest

from sinais.core.config import Ambiente, ErroConfiguracao, carregar_configuracao

BASE = {
    "SINAIS_AMBIENTE": "dev",
    "SINAIS_DATABASE_URL": "postgresql://u:p@db/sinais",
    "SINAIS_REDIS_URL": "redis://redis:6379/0",
}


def test_carrega_valores_validos() -> None:
    cfg = carregar_configuracao(BASE)
    assert cfg.ambiente is Ambiente.DESENVOLVIMENTO
    assert cfg.database_url.get_secret_value() == "postgresql://u:p@db/sinais"
    assert cfg.redis_url.get_secret_value() == "redis://redis:6379/0"


def test_padroes() -> None:
    cfg = carregar_configuracao(BASE)
    assert cfg.nivel_log == "INFO"
    assert cfg.binance_ws_url == "wss://data-stream.binance.vision"
    assert cfg.binance_rest_url == "https://api.binance.com"


def test_sobrescreve_opcionais() -> None:
    cfg = carregar_configuracao({**BASE, "SINAIS_NIVEL_LOG": "DEBUG"})
    assert cfg.nivel_log == "DEBUG"


def test_falta_obrigatoria_nomeia_variavel() -> None:
    env = {k: v for k, v in BASE.items() if k != "SINAIS_DATABASE_URL"}
    with pytest.raises(ErroConfiguracao) as exc:
        carregar_configuracao(env)
    assert "SINAIS_DATABASE_URL" in str(exc.value)


def test_valor_invalido_nao_vaza_segredo() -> None:
    env = {
        **BASE,
        "SINAIS_AMBIENTE": "xyz",
        "SINAIS_DATABASE_URL": "postgresql://u:SEGREDO@db/x",
    }
    with pytest.raises(ErroConfiguracao) as exc:
        carregar_configuracao(env)
    assert "SINAIS_AMBIENTE" in str(exc.value)
    assert "SEGREDO" not in str(exc.value)
    assert "xyz" not in str(exc.value)


def test_repr_esconde_segredos() -> None:
    cfg = carregar_configuracao(BASE)
    assert "p@db" not in repr(cfg)
    assert "p@db" not in str(cfg)


def test_le_os_environ_por_padrao(monkeypatch: pytest.MonkeyPatch) -> None:
    for k, v in BASE.items():
        monkeypatch.setenv(k, v)
    assert carregar_configuracao().ambiente is Ambiente.DESENVOLVIMENTO


@pytest.mark.parametrize(
    ("var", "valor"),
    [
        ("SINAIS_DATABASE_URL", ""),
        ("SINAIS_DATABASE_URL", "nada"),
        ("SINAIS_DATABASE_URL", "mysql://u:p@db/x"),
        ("SINAIS_REDIS_URL", ""),
        ("SINAIS_REDIS_URL", "nada"),
    ],
)
def test_url_vazia_ou_malformada_rejeita(var: str, valor: str) -> None:
    with pytest.raises(ErroConfiguracao) as exc:
        carregar_configuracao({**BASE, var: valor})
    assert var in str(exc.value)
    if valor:
        assert valor not in str(exc.value)


@pytest.mark.parametrize(
    "url", ["postgresql://u:p@db/x", "postgresql+asyncpg://u:p@db/x", "postgres://u:p@db/x"]
)
def test_esquemas_postgres_aceitos(url: str) -> None:
    assert carregar_configuracao({**BASE, "SINAIS_DATABASE_URL": url})


def test_esquema_rediss_aceito() -> None:
    assert carregar_configuracao({**BASE, "SINAIS_REDIS_URL": "rediss://r:6380/0"})
