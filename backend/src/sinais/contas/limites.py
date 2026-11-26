"""Limites de tentativas (rate limit) e bloqueio progressivo de login (design §15).

O bloqueio progressivo vale por (e-mail, IP): um atacante não trava o dono da conta, que entra
de outro IP. Um teto global por e-mail, bem mais alto, segura o ataque distribuído; um
dispositivo em que a conta já entrou (cookie assinado "dispositivo confiável") não é barrado por
esse teto, só pelo bloqueio do seu próprio IP. As chaves usam hash, existente ou não o e-mail:
quem tenta adivinhar contas recebe as mesmas respostas. IPv6 conta por bloco /64 (um único
cliente costuma ter o /64 inteiro).
"""

from __future__ import annotations

from dataclasses import dataclass
from ipaddress import IPv6Address, ip_address, ip_network
from typing import Protocol

from sinais.core.tempo import InstanteMs, Relogio


def chave_ip(ip: str) -> str:
    """IP usado nos contadores: IPv6 vira o bloco /64; IPv4 mapeado em IPv6 vira o IPv4."""
    try:
        end = ip_address(ip.strip())
    except ValueError:
        return ip
    if isinstance(end, IPv6Address):
        if end.ipv4_mapped is not None:
            return str(end.ipv4_mapped)
        return str(ip_network(f"{end}/64", strict=False))
    return str(end)


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
    # Teto global por e-mail (todos os IPs somados), contra ataque distribuído.
    falhas_globais_email: int = 50
    janela_global_s: int = 3600
    bloqueio_global_s: int = 900

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
