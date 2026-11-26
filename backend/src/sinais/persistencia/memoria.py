"""Repositório em memória: dublê de testes com o mesmo contrato do PostgreSQL."""

from __future__ import annotations

from collections.abc import Sequence

from sinais.core.tempo import InstanteMs
from sinais.dados.modelos import Candle, IntervaloColeta
from sinais.dados.qualidade import Lacuna
from sinais.persistencia.repositorio import EventoQualidade

_POR_DURACAO = {i.duracao_ms: i for i in IntervaloColeta}


class RepositorioCandlesMemoria:
    def __init__(self) -> None:
        self._dados: dict[tuple[IntervaloColeta, str], dict[InstanteMs, Candle]] = {}
        self._qualidade: list[EventoQualidade] = []

    async def inserir(self, candles: Sequence[Candle]) -> int:
        novos = 0
        for c in candles:
            serie = self._dados.setdefault((_POR_DURACAO[c.intervalo_ms], c.simbolo), {})
            if c.abertura not in serie:
                serie[c.abertura] = c
                novos += 1
        return novos

    async def ultima_abertura(self, simbolo: str, intervalo: IntervaloColeta) -> InstanteMs | None:
        serie = self._dados.get((intervalo, simbolo))
        return max(serie) if serie else None

    async def listar(
        self, simbolo: str, intervalo: IntervaloColeta, inicio: InstanteMs, fim: InstanteMs
    ) -> list[Candle]:
        serie = self._dados.get((intervalo, simbolo), {})
        return [serie[t] for t in sorted(serie) if inicio <= t < fim]

    async def registrar_qualidade(
        self, simbolo: str, intervalo: IntervaloColeta, lacuna: Lacuna, tipo: str
    ) -> None:
        self._qualidade.append((simbolo, intervalo.value, lacuna.inicio, lacuna.fim, tipo))

    async def eventos_qualidade(self, simbolo: str) -> list[EventoQualidade]:
        return [e for e in self._qualidade if e[0] == simbolo]

    def todos_eventos_qualidade(self) -> list[EventoQualidade]:
        return list(self._qualidade)
