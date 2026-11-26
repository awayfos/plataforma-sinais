"""Primitivas de segurança: tokens opacos, hash de token e cifra do segredo TOTP (AES-GCM)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_NONCE = 12


class ErroCifra(Exception):
    """Texto cifrado inválido, adulterado ou de outra chave."""


def gerar_token() -> str:
    """256 bits aleatórios em base64 url-safe."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """O banco guarda só o SHA-256: um vazamento do banco não entrega sessões válidas."""
    return hashlib.sha256(token.encode()).hexdigest()


def iguais(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


class CifraSegredos:
    """AES-GCM com prefixo de identificação da chave (``k1:``, para rotação) e dado associado
    (``contexto``, ex.: ``usuario:7``): um segredo copiado para a linha de outro usuário não
    decifra."""

    def __init__(self, chave: bytes, id_chave: str = "k1") -> None:
        if len(chave) != 32:
            raise ValueError("a chave de cifra deve ter 32 bytes")
        if not id_chave or ":" in id_chave:
            raise ValueError("identificador de chave inválido")
        self._aes = AESGCM(chave)
        self._id = id_chave

    @classmethod
    def de_base64(cls, texto: str, id_chave: str = "k1") -> CifraSegredos:
        return cls(base64.urlsafe_b64decode(texto.encode()), id_chave)

    def cifrar(self, texto: str, contexto: str = "") -> str:
        nonce = os.urandom(_NONCE)
        corpo = nonce + self._aes.encrypt(nonce, texto.encode(), contexto.encode())
        return f"{self._id}:" + base64.urlsafe_b64encode(corpo).decode()

    def decifrar(self, cifrado: str, contexto: str = "") -> str:
        id_chave, _, resto = cifrado.partition(":")
        if id_chave != self._id or not resto:
            raise ErroCifra("segredo cifrado com outra chave ou sem identificação")
        try:
            bruto = base64.urlsafe_b64decode(resto.encode())
            return self._aes.decrypt(bruto[:_NONCE], bruto[_NONCE:], contexto.encode()).decode()
        except (InvalidTag, ValueError) as erro:
            raise ErroCifra("segredo cifrado inválido") from erro
