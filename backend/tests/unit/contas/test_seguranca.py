import base64

import pytest

from sinais.contas.seguranca import CifraSegredos, ErroCifra, gerar_token, hash_token, iguais


def test_token_aleatorio_longo_e_url_safe() -> None:
    a, b = gerar_token(), gerar_token()
    assert a != b
    assert len(a) >= 43
    assert set(a) <= set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")


def test_hash_token_sha256_hex_deterministico() -> None:
    assert hash_token("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert hash_token("abc") != hash_token("abd")


def test_iguais_compara_textos() -> None:
    assert iguais("x1", "x1")
    assert not iguais("x1", "x2")
    assert not iguais("", "x")


def test_cifra_ida_e_volta_e_nao_deterministica() -> None:
    c = CifraSegredos(bytes(range(32)))
    a, b = c.cifrar("JBSWY3DPEHPK3PXP"), c.cifrar("JBSWY3DPEHPK3PXP")
    assert a != b
    assert "JBSWY3DP" not in a
    assert c.decifrar(a) == "JBSWY3DPEHPK3PXP"


def test_cifra_recusa_chave_errada_e_adulteracao() -> None:
    texto = CifraSegredos(bytes(range(32))).cifrar("segredo")
    with pytest.raises(ErroCifra):
        CifraSegredos(bytes(32)).decifrar(texto)
    prefixo, _, corpo = texto.partition(":")
    bruto = bytearray(base64.urlsafe_b64decode(corpo))
    bruto[-1] ^= 1
    with pytest.raises(ErroCifra):
        CifraSegredos(bytes(range(32))).decifrar(
            prefixo + ":" + base64.urlsafe_b64encode(bytes(bruto)).decode()
        )


def test_cifra_exige_chave_de_32_bytes_e_aceita_base64() -> None:
    with pytest.raises(ValueError):
        CifraSegredos(b"curta")
    chave = base64.urlsafe_b64encode(bytes(range(32))).decode()
    assert (
        CifraSegredos.de_base64(chave).decifrar(CifraSegredos(bytes(range(32))).cifrar("s")) == "s"
    )


def test_cifra_amarra_ao_usuario_e_identifica_a_chave() -> None:
    c = CifraSegredos(bytes(range(32)), id_chave="k1")
    texto = c.cifrar("segredo", "usuario:7")
    assert texto.startswith("k1:")
    assert c.decifrar(texto, "usuario:7") == "segredo"
    with pytest.raises(ErroCifra):  # segredo de outro usuário copiado para esta linha
        c.decifrar(texto, "usuario:8")
    with pytest.raises(ErroCifra):  # cifrado com outra chave
        CifraSegredos(bytes(range(32)), id_chave="k2").decifrar(texto, "usuario:7")
