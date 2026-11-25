"""Repositório de candles no PostgreSQL/TimescaleDB."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import Table, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine

from sinais.core.tempo import InstanteMs, de_datetime, para_datetime
from sinais.dados.modelos import Candle, IntervaloColeta
from sinais.dados.qualidade import Lacuna
from sinais.persistencia.repositorio import EventoQualidade
from sinais.persistencia.tabelas import candles_1m, candles_1s, eventos_qualidade

_TABELAS: dict[int, Table] = {
    IntervaloColeta.M1.duracao_ms: candles_1m,
    IntervaloColeta.S1.duracao_ms: candles_1s,
}
_LOTE = 1000
_CAMPOS = (
    "abertura_preco",
    "maxima",
    "minima",
    "fechamento",
    "volume",
    "volume_cotacao",
    "negocios",
    "volume_compra_agressora",
    "fonte",
)


def _linha(c: Candle) -> dict[str, Any]:
    d: dict[str, Any] = {campo: getattr(c, campo) for campo in _CAMPOS}
    d["simbolo"] = c.simbolo
    d["abertura"] = para_datetime(c.abertura)
    return d


def _candle(linha: Any, intervalo_ms: int) -> Candle:
    return Candle(
        simbolo=linha.simbolo,
        intervalo_ms=intervalo_ms,
        abertura=de_datetime(linha.abertura),
        **{campo: getattr(linha, campo) for campo in _CAMPOS},
    )


class RepositorioCandlesPg:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def inserir(self, candles: Sequence[Candle]) -> int:
        novos = 0
        por_tabela: dict[int, list[Candle]] = {}
        for c in candles:
            por_tabela.setdefault(c.intervalo_ms, []).append(c)
        async with self._engine.begin() as conn:
            for intervalo_ms, grupo in por_tabela.items():
                tabela = _TABELAS[intervalo_ms]
                for i in range(0, len(grupo), _LOTE):
                    stmt = (
                        insert(tabela)
                        .values([_linha(c) for c in grupo[i : i + _LOTE]])
                        .on_conflict_do_nothing(index_elements=["simbolo", "abertura"])
                        .returning(tabela.c.abertura)
                    )
                    novos += len((await conn.execute(stmt)).all())
        return novos

    async def ultima_abertura(self, simbolo: str, intervalo: IntervaloColeta) -> InstanteMs | None:
        tabela = _TABELAS[intervalo.duracao_ms]
        async with self._engine.connect() as conn:
            valor = await conn.scalar(
                select(func.max(tabela.c.abertura)).where(tabela.c.simbolo == simbolo)
            )
        return None if valor is None else de_datetime(valor)

    async def listar(
        self, simbolo: str, intervalo: IntervaloColeta, inicio: InstanteMs, fim: InstanteMs
    ) -> list[Candle]:
        tabela = _TABELAS[intervalo.duracao_ms]
        stmt = (
            select(tabela)
            .where(
                tabela.c.simbolo == simbolo,
                tabela.c.abertura >= para_datetime(inicio),
                tabela.c.abertura < para_datetime(fim),
            )
            .order_by(tabela.c.abertura)
        )
        async with self._engine.connect() as conn:
            linhas = (await conn.execute(stmt)).all()
        return [_candle(linha, intervalo.duracao_ms) for linha in linhas]

    async def registrar_qualidade(
        self, simbolo: str, intervalo: IntervaloColeta, lacuna: Lacuna, tipo: str
    ) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                eventos_qualidade.insert().values(
                    simbolo=simbolo,
                    intervalo=intervalo.value,
                    inicio=para_datetime(lacuna.inicio),
                    fim=para_datetime(lacuna.fim),
                    tipo=tipo,
                )
            )

    async def eventos_qualidade(self, simbolo: str) -> list[EventoQualidade]:
        t = eventos_qualidade
        stmt = (
            select(t.c.simbolo, t.c.intervalo, t.c.inicio, t.c.fim, t.c.tipo)
            .where(t.c.simbolo == simbolo)
            .order_by(t.c.id)
        )
        async with self._engine.connect() as conn:
            linhas = (await conn.execute(stmt)).all()
        return [(s, i, de_datetime(a), de_datetime(b), tp) for s, i, a, b, tp in linhas]
