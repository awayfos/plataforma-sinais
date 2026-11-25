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
