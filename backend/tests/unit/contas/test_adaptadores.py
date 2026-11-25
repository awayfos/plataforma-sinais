"""Adaptadores reais (argon2-cffi e pyotp). Rodam no CI, onde as bibliotecas estão instaladas."""

import pytest

from sinais.contas.senhas import HasherArgon2
from sinais.contas.totp import TotpPyotp

T0 = 1795575600000


def test_argon2id_gera_verifica_e_recusa() -> None:
    pytest.importorskip("argon2")
    h = HasherArgon2()
    hash_ = h.gerar("senha-forte-123")
    assert hash_.startswith("$argon2id$")
    assert "senha-forte-123" not in hash_
    assert h.verificar(hash_, "senha-forte-123")
    assert not h.verificar(hash_, "senha-errada-1")
    assert not h.verificar("lixo", "senha-forte-123")
    assert not h.precisa_rehash(hash_)


def test_totp_aceita_passo_atual_e_vizinho_e_recusa_resto() -> None:
    pyotp = pytest.importorskip("pyotp")
    t = TotpPyotp()
    segredo = t.novo_segredo()
    gerador = pyotp.TOTP(segredo)
    passo = T0 // 1000 // 30
    assert t.passo_valido(segredo, gerador.at(T0 // 1000), T0) == passo
    assert t.passo_valido(segredo, gerador.at(T0 // 1000 - 30), T0) == passo - 1
    assert t.passo_valido(segredo, gerador.at(T0 // 1000 + 90), T0) is None
    assert t.passo_valido(segredo, "12345", T0) is None
    assert t.passo_valido(segredo, "abcdef", T0) is None
    uri = t.uri(segredo, "admin@exemplo.com")
    assert uri.startswith("otpauth://totp/") and f"secret={segredo}" in uri and "Sinais" in uri
