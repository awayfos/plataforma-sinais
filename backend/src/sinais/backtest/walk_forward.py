"""Walk-forward por meses UTC: treino → calibração → teste, avançando um mês de teste por vez.

``purgar`` remove do treino (ou da calibração) as amostras cujo rótulo termina dentro do
embargo ou depois do início do período seguinte, para que nenhum rótulo "veja" o teste.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pandas as pd

from sinais.core.tempo import InstanteMs, de_datetime, para_datetime


@dataclass(frozen=True)
class Dobra:
    treino: tuple[InstanteMs, InstanteMs]
    calibracao: tuple[InstanteMs, InstanteMs]
    teste: tuple[InstanteMs, InstanteMs]


def _somar_meses(t: InstanteMs, meses: int) -> InstanteMs:
    dt = para_datetime(t)
    total = dt.year * 12 + dt.month - 1 + meses
    return de_datetime(datetime(total // 12, total % 12 + 1, 1, tzinfo=UTC))


def dobras(
    inicio: InstanteMs,
    fim: InstanteMs,
    treino_meses: int = 6,
    calibracao_meses: int = 1,
    teste_meses: int = 1,
    holdout_meses: int = 3,
) -> list[Dobra]:
    """Dobras dentro de ``[inicio, fim)``, deixando os últimos ``holdout_meses`` intocados
    para a avaliação final (design §13.2). ``inicio`` é levado ao primeiro dia do mês."""
    fim = _somar_meses(fim, -holdout_meses) if holdout_meses else fim
    base = _somar_meses(inicio, 0)
    if base < inicio:
        base = _somar_meses(base, 1)
    saida: list[Dobra] = []
    while True:
        t1 = _somar_meses(base, treino_meses)
        c1 = _somar_meses(t1, calibracao_meses)
        e1 = _somar_meses(c1, teste_meses)
        if e1 > fim:
            return saida
        saida.append(Dobra((base, t1), (t1, c1), (c1, e1)))
        base = _somar_meses(base, teste_meses)


def purgar(fim_rotulo: pd.Series, ate: InstanteMs, embargo_ms: int) -> pd.Series:
    """True para amostras cujo rótulo termina até ``ate - embargo``. Use o vencimento real de
    cada sinal (com vencimento no relógio ele varia até ``2 x grade - corte`` após a decisão)."""
    return fim_rotulo <= (ate - embargo_ms)
