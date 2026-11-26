"""Níveis de suporte/resistência com o instante de cada toque (design §4 e §9c).

Mesma fusão de ``analise.regioes.Niveis`` (pivô dentro de ``tolerancia`` do nível mais próximo vira
toque e o preço do nível passa a ser a média dos toques), mas guardando **quando** cada toque
aconteceu: assim dá para contar só os toques das últimas 4 h, saber a ordem do toque e o tempo entre
toques. O instante de um toque é o do candle do pivô; ele só entra quando o pivô é confirmado.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

_MINUTO_MS = 60_000


@dataclass
class Nivel:
    preco: float
    toques: list[int] = field(default_factory=list)


class Zonas:
    def __init__(self, maximo: int = 60) -> None:
        self._maximo = maximo
        self._niveis: list[Nivel] = []

    def niveis(self) -> list[Nivel]:
        return list(self._niveis)

    def adicionar(self, preco: float, tolerancia: float, t: int) -> None:
        if self._niveis:
            mais_perto = min(self._niveis, key=lambda n: abs(n.preco - preco))
            if abs(mais_perto.preco - preco) <= tolerancia:
                k = len(mais_perto.toques)
                mais_perto.preco = (mais_perto.preco * k + preco) / (k + 1)
                mais_perto.toques.append(t)
                return
        self._niveis.append(Nivel(preco, [t]))
        if len(self._niveis) > self._maximo:
            self._niveis.remove(min(self._niveis, key=lambda n: n.toques[-1]))

    def rompidos(self, c_ant: float, c_atual: float) -> list[Nivel]:
        """Níveis cruzados pelo fechamento: ``c_ant ≤ P < c_atual`` (alta) ou
        ``c_ant ≥ P > c_atual`` (baixa), em ordem de preço."""
        if c_atual > c_ant:
            saida = [n for n in self._niveis if c_ant <= n.preco < c_atual]
        elif c_atual < c_ant:
            saida = [n for n in self._niveis if c_atual < n.preco <= c_ant]
        else:
            saida = []
        return sorted(saida, key=lambda n: n.preco)

    @staticmethod
    def toques_em(nivel: Nivel, t: int, janela_ms: int) -> int:
        return sum(1 for x in nivel.toques if t - janela_ms <= x <= t)

    @staticmethod
    def min_entre_toques(nivel: Nivel, t: int, janela_ms: int) -> float:
        recentes = [x for x in nivel.toques if t - janela_ms <= x <= t]
        if len(recentes) < 2:
            return math.nan
        return (recentes[-1] - recentes[-2]) / _MINUTO_MS
