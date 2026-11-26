import base64

import pytest

from sinais.api.config import carregar_configuracao_api
from sinais.core.config import ErroConfiguracao

CHAVE = base64.urlsafe_b64encode(bytes(range(32))).decode()


def test_padroes_e_listas() -> None:
    cfg = carregar_configuracao_api(
        {"SINAIS_CHAVE_CIFRA": CHAVE, "SINAIS_ORIGENS_PERMITIDAS": "https://a.com, https://b.com"}
    )
    assert cfg.cookie_seguro is True and cfg.sessoes_simultaneas == 1
    assert cfg.origens_permitidas == ("https://a.com", "https://b.com")
    assert cfg.chave_cifra.get_secret_value() == CHAVE


@pytest.mark.parametrize("chave", [None, "curta", base64.urlsafe_b64encode(b"x" * 16).decode()])
def test_chave_invalida_nao_vaza_valor(chave: str | None) -> None:
    env = {} if chave is None else {"SINAIS_CHAVE_CIFRA": chave}
    with pytest.raises(ErroConfiguracao) as e:
        carregar_configuracao_api(env)
    assert "SINAIS_CHAVE_CIFRA" in str(e.value)
    if chave:
        assert chave not in str(e.value)


def test_padrao_de_desenvolvimento_aceita_o_frontend_local() -> None:
    cfg = carregar_configuracao_api({"SINAIS_CHAVE_CIFRA": CHAVE})
    assert cfg.origens_permitidas == ("http://localhost:3000",)
    assert cfg.proxies_confiaveis == ()


def test_proxies_confiaveis_em_cidr() -> None:
    cfg = carregar_configuracao_api(
        {"SINAIS_CHAVE_CIFRA": CHAVE, "SINAIS_PROXIES_CONFIAVEIS": "127.0.0.1/32, 172.16.0.0/12"}
    )
    assert [str(r) for r in cfg.proxies_confiaveis] == ["127.0.0.1/32", "172.16.0.0/12"]
    with pytest.raises(ErroConfiguracao) as e:
        carregar_configuracao_api({"SINAIS_CHAVE_CIFRA": CHAVE, "SINAIS_PROXIES_CONFIAVEIS": "x"})
    assert "SINAIS_PROXIES_CONFIAVEIS" in str(e.value)


def test_producao_exige_origens_e_recusa_a_chave_de_exemplo() -> None:
    exemplo = "ZGVzZW52b2x2aW1lbnRvLW5hby11c2UtZW0tcHJvZCE="
    base = {"SINAIS_AMBIENTE": "prod", "SINAIS_ORIGENS_PERMITIDAS": "https://app.exemplo.com"}
    assert carregar_configuracao_api({**base, "SINAIS_CHAVE_CIFRA": CHAVE}).ambiente == "prod"
    with pytest.raises(ErroConfiguracao) as e:
        carregar_configuracao_api({**base, "SINAIS_CHAVE_CIFRA": exemplo})
    assert "SINAIS_CHAVE_CIFRA" in str(e.value) and exemplo not in str(e.value)
    with pytest.raises(ErroConfiguracao) as e:
        carregar_configuracao_api({"SINAIS_AMBIENTE": "prod", "SINAIS_CHAVE_CIFRA": CHAVE})
    assert "SINAIS_ORIGENS_PERMITIDAS" in str(e.value)
