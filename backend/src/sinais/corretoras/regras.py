"""Regras de vencimento e liquidação de opções binárias (perfil da plataforma Quadcode).

Na Exnova o vencimento é alinhado ao relógio: a compra vale para o primeiro múltiplo da grade
que ainda tenha pelo menos ``corte`` pela frente. Ex.: 1 min (corte 30 s): compra às 00:30:10
vence às 00:31:00; às 00:30:30 já vence às 00:32:00.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from sinais.core.dominio import Direcao, Expiracao
from sinais.core.tempo import InstanteMs, validar_instante


@dataclass(frozen=True, slots=True)
class RegraVencimento:
    grade_ms: int
    corte_ms: int

    def vencimento_para(self, compra: InstanteMs) -> InstanteMs:
        validar_instante(compra)
        proximo = compra - compra % self.grade_ms + self.grade_ms
        return proximo if proximo - compra > self.corte_ms else proximo + self.grade_ms

    def prazo_compra(self, vencimento: InstanteMs) -> InstanteMs:
        """Último instante (inclusive) em que a compra ainda vale para ``vencimento``."""
        return vencimento - self.corte_ms - 1


@dataclass(frozen=True)
class PerfilCorretora:
    nome: str
    regras: Mapping[Expiracao, RegraVencimento]
    payout: Mapping[Expiracao, float]
    hipoteses: frozenset[Expiracao] = field(default_factory=frozenset)


def _regra(minutos: int, corte_s: int) -> RegraVencimento:
    return RegraVencimento(minutos * 60_000, corte_s * 1000)


EXNOVA = PerfilCorretora(
    nome="Exnova",
    regras={
        Expiracao.M1: _regra(1, 30),  # confirmado pelo cliente
        Expiracao.M5: _regra(5, 100),  # hipótese: 1/3 da grade
        Expiracao.M15: _regra(15, 300),  # confirmado pelo cliente
        Expiracao.M30: _regra(30, 600),  # hipótese
        Expiracao.H1: _regra(60, 1200),  # hipótese
    },
    payout={e: 0.85 for e in Expiracao},  # hipotético até o cliente informar
    hipoteses=frozenset({Expiracao.M5, Expiracao.M30, Expiracao.H1}),
)


class Resultado(StrEnum):
    WIN = "WIN"
    LOSS = "LOSS"
    TIE = "TIE"


def liquidar(direcao: Direcao, entrada: float, vencimento: float) -> Resultado:
    if vencimento == entrada:
        return Resultado.TIE
    subiu = vencimento > entrada
    ganhou = subiu if direcao is Direcao.COMPRA else not subiu
    return Resultado.WIN if ganhou else Resultado.LOSS


def ponto_equilibrio(payout: float) -> float:
    """Taxa de acerto mínima para valor esperado zero: ``1 / (1 + payout)``."""
    return 1.0 / (1.0 + payout)
