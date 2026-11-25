"""Verificação de sequência de candles: lacunas, duplicados e fora de ordem."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sinais.core.tempo import InstanteMs
from sinais.dados.modelos import Candle


@dataclass(frozen=True, slots=True)
class Lacuna:
    inicio: InstanteMs
    fim: InstanteMs  # exclusivo


@dataclass(frozen=True, slots=True)
class RelatorioQualidade:
    lacunas: tuple[Lacuna, ...] = ()
    duplicados: tuple[InstanteMs, ...] = ()
    fora_de_ordem: tuple[InstanteMs, ...] = ()

    @property
    def ok(self) -> bool:
        return not (self.lacunas or self.duplicados or self.fora_de_ordem)


def verificar_sequencia(candles: Sequence[Candle], intervalo_ms: int) -> RelatorioQualidade:
    lacunas: list[Lacuna] = []
    duplicados: list[InstanteMs] = []
    fora: list[InstanteMs] = []
    maior: InstanteMs | None = None
    for c in candles:
        if maior is None:
            maior = c.abertura
            continue
        if c.abertura == maior:
            duplicados.append(c.abertura)
        elif c.abertura < maior:
            fora.append(c.abertura)
        else:
            esperado = maior + intervalo_ms
            if c.abertura > esperado:
                lacunas.append(Lacuna(esperado, c.abertura))
            maior = c.abertura
    return RelatorioQualidade(tuple(lacunas), tuple(duplicados), tuple(fora))
