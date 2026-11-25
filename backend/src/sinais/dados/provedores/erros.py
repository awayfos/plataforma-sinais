"""Erros comuns dos provedores de dados (sem dependência de bibliotecas de I/O)."""

from __future__ import annotations


class ErroLimiteTaxa(Exception):
    """O provedor bloqueou o IP (na Binance, HTTP 418). Esperar ``espera_s`` antes de tentar."""

    def __init__(self, espera_s: float) -> None:
        super().__init__(f"limite de requisições do provedor: aguardar {espera_s:.0f} s")
        self.espera_s = espera_s
