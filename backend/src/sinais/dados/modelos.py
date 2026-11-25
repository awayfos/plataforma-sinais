"""Modelo de candle fechado usado em toda a coleta."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from sinais.core.tempo import InstanteMs, validar_instante


class IntervaloColeta(StrEnum):
    """Intervalos coletados da fonte. Tempos gráficos maiores derivam de 1m."""

    S1 = "1s"
    M1 = "1m"

    @property
    def duracao_ms(self) -> int:
        return 1000 if self is IntervaloColeta.S1 else 60_000


@dataclass(frozen=True, slots=True)
class Candle:
    simbolo: str
    intervalo_ms: int
    abertura: InstanteMs
    abertura_preco: Decimal
    maxima: Decimal
    minima: Decimal
    fechamento: Decimal
    volume: Decimal
    volume_cotacao: Decimal
    negocios: int
    volume_compra_agressora: Decimal
    fonte: str

    def __post_init__(self) -> None:
        validar_instante(self.abertura)
        if self.intervalo_ms <= 0:
            raise ValueError(f"intervalo inválido: {self.intervalo_ms}")
        if self.abertura % self.intervalo_ms != 0 and self.intervalo_ms < 604_800_000:
            raise ValueError(f"{self.simbolo}: abertura {self.abertura} não alinhada")
        if self.maxima < max(self.abertura_preco, self.fechamento, self.minima):
            raise ValueError(f"{self.simbolo} {self.abertura}: máxima menor que o corpo")
        if self.minima > min(self.abertura_preco, self.fechamento):
            raise ValueError(f"{self.simbolo} {self.abertura}: mínima maior que o corpo")
        if min(self.volume, self.volume_cotacao, self.volume_compra_agressora) < 0:
            raise ValueError(f"{self.simbolo} {self.abertura}: volume negativo")
        if self.negocios < 0:
            raise ValueError(f"{self.simbolo} {self.abertura}: negócios negativos")

    @property
    def fechamento_ms(self) -> InstanteMs:
        return self.abertura + self.intervalo_ms
