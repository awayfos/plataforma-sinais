"""Tipos de domínio e alinhamento de candles em UTC."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum

from sinais.core.tempo import InstanteMs, validar_instante

_MINUTO_MS = 60_000
_DIA_MS = 86_400_000
# A época Unix (1970-01-01) foi numa quinta; a primeira segunda é 1970-01-05.
_DESLOCAMENTO_SEGUNDA_MS = 4 * _DIA_MS


class TempoGrafico(StrEnum):
    M1 = "1m"
    M3 = "3m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"

    @property
    def duracao_ms(self) -> int:
        return _DURACOES_MS[self]


_DURACOES_MS: dict[TempoGrafico, int] = {
    TempoGrafico.M1: _MINUTO_MS,
    TempoGrafico.M3: 3 * _MINUTO_MS,
    TempoGrafico.M5: 5 * _MINUTO_MS,
    TempoGrafico.M15: 15 * _MINUTO_MS,
    TempoGrafico.M30: 30 * _MINUTO_MS,
    TempoGrafico.H1: 60 * _MINUTO_MS,
    TempoGrafico.H4: 240 * _MINUTO_MS,
    TempoGrafico.D1: _DIA_MS,
    TempoGrafico.W1: 7 * _DIA_MS,
}


def abertura_candle(instante: InstanteMs, tg: TempoGrafico) -> InstanteMs:
    """Início do candle que contém ``instante``. A semana começa segunda 00:00 UTC."""
    validar_instante(instante)
    if tg is TempoGrafico.W1:
        return instante - (instante - _DESLOCAMENTO_SEGUNDA_MS) % tg.duracao_ms
    return instante - instante % tg.duracao_ms


def fechamento_candle(instante: InstanteMs, tg: TempoGrafico) -> InstanteMs:
    """Fim (exclusivo) do candle que contém ``instante``."""
    return abertura_candle(instante, tg) + tg.duracao_ms


class Expiracao(IntEnum):
    """Expirações da V1, em segundos."""

    M1 = 60
    M5 = 300
    M15 = 900
    M30 = 1800
    H1 = 3600


class Direcao(StrEnum):
    COMPRA = "BUY"
    VENDA = "SELL"
    AGUARDAR = "WAIT"


class ClasseAtivo(StrEnum):
    CRIPTO = "cripto"
    FOREX = "forex"
    METAL = "metal"
    ACAO = "acao"


@dataclass(frozen=True, slots=True)
class Ativo:
    simbolo: str
    classe: ClasseAtivo
    provedor: str
    simbolo_provedor: str
    precisao_preco: int

    def __post_init__(self) -> None:
        if not self.simbolo or self.simbolo != self.simbolo.upper():
            raise ValueError(f"símbolo inválido: {self.simbolo!r} (não vazio, em maiúsculas)")
        if not 0 <= self.precisao_preco <= 12:
            raise ValueError(f"precisão de preço fora de 0..12: {self.precisao_preco}")


ATIVOS_V1: tuple[Ativo, ...] = (
    Ativo("BTCUSDT", ClasseAtivo.CRIPTO, "binance", "BTCUSDT", 2),
    Ativo("ETHUSDT", ClasseAtivo.CRIPTO, "binance", "ETHUSDT", 2),
)
