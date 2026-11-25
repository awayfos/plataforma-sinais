"""Fonte de histórico falsa: candles sintéticos para qualquer janela, com lacunas opcionais."""

from decimal import Decimal

from sinais.core.tempo import InstanteMs
from sinais.dados.modelos import Candle, IntervaloColeta


def sintetico(simbolo: str, intervalo: IntervaloColeta, t: InstanteMs) -> Candle:
    p = Decimal(100 + (t // intervalo.duracao_ms) % 7)
    return Candle(
        simbolo,
        intervalo.duracao_ms,
        t,
        p,
        p + 1,
        p - 1,
        p,
        Decimal(1),
        p,
        1,
        Decimal("0.5"),
        "teste",
    )


class FonteFalsa:
    def __init__(self, faltando: set[InstanteMs] | None = None) -> None:
        self.faltando = faltando or set()
        self.chamadas: list[tuple[str, str, InstanteMs, InstanteMs]] = []

    async def klines(
        self,
        simbolo: str,
        intervalo: IntervaloColeta,
        inicio: InstanteMs,
        fim: InstanteMs,
        limite: int = 1000,
    ) -> list[Candle]:
        self.chamadas.append((simbolo, intervalo.value, inicio, fim))
        d = intervalo.duracao_ms
        return [
            sintetico(simbolo, intervalo, t)
            for t in range(inicio, fim, d)
            if t not in self.faltando
        ][:limite]
