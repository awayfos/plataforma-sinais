"""Hash de senhas com Argon2id (ADR-12)."""

from __future__ import annotations

from typing import Protocol


class Hasher(Protocol):
    def gerar(self, senha: str) -> str: ...

    def verificar(self, hash_: str, senha: str) -> bool: ...

    def precisa_rehash(self, hash_: str) -> bool: ...


class HasherArgon2:
    """Argon2id com os parâmetros padrão do argon2-cffi (perfil RFC 9106 de baixa memória)."""

    def __init__(self) -> None:
        from argon2 import PasswordHasher, Type

        self._ph = PasswordHasher(type=Type.ID)

    def gerar(self, senha: str) -> str:
        return str(self._ph.hash(senha))

    def verificar(self, hash_: str, senha: str) -> bool:
        from argon2.exceptions import InvalidHashError, VerificationError

        try:
            return bool(self._ph.verify(hash_, senha))
        except (VerificationError, InvalidHashError):
            return False

    def precisa_rehash(self, hash_: str) -> bool:
        return bool(self._ph.check_needs_rehash(hash_))
