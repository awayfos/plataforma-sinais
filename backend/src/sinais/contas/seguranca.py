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
    def __init__(self, chave: bytes) -> None:
        if len(chave) != 32:
            raise ValueError("a chave de cifra deve ter 32 bytes")
        self._aes = AESGCM(chave)

    @classmethod
    def de_base64(cls, texto: str) -> CifraSegredos:
        return cls(base64.urlsafe_b64decode(texto.encode()))

    def cifrar(self, texto: str) -> str:
        nonce = os.urandom(_NONCE)
        return base64.urlsafe_b64encode(
            nonce + self._aes.encrypt(nonce, texto.encode(), None)
        ).decode()

    def decifrar(self, cifrado: str) -> str:
        try:
            bruto = base64.urlsafe_b64decode(cifrado.encode())
            return self._aes.decrypt(bruto[:_NONCE], bruto[_NONCE:], None).decode()
        except (InvalidTag, ValueError) as erro:
            raise ErroCifra("segredo cifrado inválido") from erro
