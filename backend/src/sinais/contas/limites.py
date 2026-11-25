"""Limites de tentativas (rate limit) e bloqueio progressivo de login (design §15).

As chaves usam o hash do e-mail, existente ou não: quem tenta adivinhar contas recebe as
mesmas respostas e o mesmo bloqueio para e-mails cadastrados e inexistentes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sinais.core.tempo import InstanteMs, Relogio


class ContadorLimites(Protocol):
    async def incrementar(self, chave: str, janela_s: int) -> int:
        """Soma 1 no contador da janela fixa que começa no primeiro incremento."""
        ...

    async def ler(self, chave: str) -> str | None: ...

    async def gravar(self, chave: str, valor: str, validade_s: int) -> None: ...

    async def apagar(self, chave: str) -> None: ...


@dataclass(frozen=True, slots=True)
class PoliticaLogin:
    tentativas_por_ip: int = 20
    tentativas_por_email: int = 10
    janela_s: int = 60
    falhas_para_bloqueio: int = 5
    bloqueio_inicial_s: int = 60
    bloqueio_maximo_s: int = 1800
    memoria_falhas_s: int = 86_400

    def bloqueio_s(self, falhas: int) -> int:
        """Bloqueio após ``falhas`` seguidas: 60 s na 5ª, dobra a cada nova, teto 30 min."""
        if falhas < self.falhas_para_bloqueio:
            return 0
        expoente = min(falhas - self.falhas_para_bloqueio, 20)
        return min(self.bloqueio_inicial_s << expoente, self.bloqueio_maximo_s)


class ContadorMemoria:
    """Contador em memória com validade pelo relógio injetado (testes e processo único)."""

    def __init__(self, relogio: Relogio) -> None:
        self._relogio = relogio
        self._dados: dict[str, tuple[str, InstanteMs]] = {}

    def _vivo(self, chave: str) -> str | None:
        item = self._dados.get(chave)
        if item is None:
            return None
        if item[1] <= self._relogio.agora_ms():
            del self._dados[chave]
            return None
        return item[0]

    async def incrementar(self, chave: str, janela_s: int) -> int:
        atual = self._vivo(chave)
        if atual is None:
            self._dados[chave] = ("1", self._relogio.agora_ms() + janela_s * 1000)
            return 1
        n = int(atual) + 1
        self._dados[chave] = (str(n), self._dados[chave][1])
        return n

    async def ler(self, chave: str) -> str | None:
        return self._vivo(chave)

    async def gravar(self, chave: str, valor: str, validade_s: int) -> None:
        self._dados[chave] = (valor, self._relogio.agora_ms() + validade_s * 1000)

    async def apagar(self, chave: str) -> None:
        self._dados.pop(chave, None)
