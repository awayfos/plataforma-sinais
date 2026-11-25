"""TOTP (RFC 6238) para o 2FA obrigatório dos administradores."""

from __future__ import annotations

import hmac
from typing import Protocol

from sinais.core.tempo import InstanteMs

PASSO_S = 30
EMISSOR = "Sinais"


class VerificadorTotp(Protocol):
    def novo_segredo(self) -> str: ...

    def passo_valido(self, segredo: str, codigo: str, agora_ms: InstanteMs) -> int | None:
        """Número do passo de 30 s em que ``codigo`` vale (tolerância de ±1 passo), ou None."""
        ...

    def uri(self, segredo: str, email: str) -> str: ...


class TotpPyotp:
    def novo_segredo(self) -> str:
        import pyotp

        return str(pyotp.random_base32())

    def passo_valido(self, segredo: str, codigo: str, agora_ms: InstanteMs) -> int | None:
        import pyotp

        if len(codigo) != 6 or not codigo.isdigit():
            return None
        totp = pyotp.TOTP(segredo)
        atual = agora_ms // 1000 // PASSO_S
        for passo in (atual - 1, atual, atual + 1):
            if hmac.compare_digest(str(totp.at(passo * PASSO_S)), codigo):
                return passo
        return None

    def uri(self, segredo: str, email: str) -> str:
        import pyotp

        return str(pyotp.TOTP(segredo).provisioning_uri(name=email, issuer_name=EMISSOR))
