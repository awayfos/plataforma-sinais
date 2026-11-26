"""Períodos da descoberta (design §9b.2): walk-forward 6/1/1 e holdout final de 3 meses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sinais.backtest.walk_forward import Dobra, _somar_meses, dobras
from sinais.core.tempo import de_datetime
from sinais.situacoes.parametros import CALIBRACAO_MESES, HOLDOUT_MESES, TREINO_MESES

Janela = tuple[int, int]


@dataclass(frozen=True)
class Periodos:
    inicio: int
    fim: int
    dobras: list[Dobra]
    holdout: Janela
    calibracao_holdout: Janela
    treino_holdout: Janela

    @property
    def meses_teste(self) -> list[Janela]:
        return [d.teste for d in self.dobras]

    @property
    def teste(self) -> Janela:
        return (self.dobras[0].teste[0], self.dobras[-1].teste[1])


def inicio_mes(am: str) -> int:
    ano, mes = (int(x) for x in am.split("-"))
    return de_datetime(datetime(ano, mes, 1, tzinfo=UTC))


def periodos_descoberta(fim_mes: str, meses: int) -> Periodos:
    """``fim_mes`` (AAAA-MM) é o último mês, inclusive; ``meses`` o total."""
    fim = _somar_meses(inicio_mes(fim_mes), 1)
    inicio = _somar_meses(fim, -meses)
    ds = dobras(inicio, fim, TREINO_MESES, CALIBRACAO_MESES, 1, HOLDOUT_MESES)
    h0 = _somar_meses(fim, -HOLDOUT_MESES)
    c0 = _somar_meses(h0, -CALIBRACAO_MESES)
    return Periodos(inicio, fim, ds, (h0, fim), (c0, h0), (_somar_meses(c0, -TREINO_MESES), c0))
