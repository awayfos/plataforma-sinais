"""Consultas de leitura para a API: candles do gráfico e eventos de qualidade recentes.

Tempos gráficos maiores que 1m são agregados a partir de ``candles_1m`` só com blocos
completos (mesma regra de ``sinais.dados.agregacao``): um bloco completo já fechou.
"""

from __future__ import annotations

from typing import Any, Protocol

from sinais.core.dominio import TempoGrafico, abertura_candle
from sinais.core.tempo import InstanteMs, de_datetime, para_datetime
from sinais.dados.agregacao import agregar
from sinais.dados.modelos import Candle, IntervaloColeta
from sinais.persistencia.memoria import RepositorioCandlesMemoria
from sinais.persistencia.repositorio import EventoQualidade

_M = 60_000
_INTERVALOS_SQL = {
    TempoGrafico.M3: "3 minutes",
    TempoGrafico.M5: "5 minutes",
    TempoGrafico.M15: "15 minutes",
    TempoGrafico.M30: "30 minutes",
    TempoGrafico.H1: "1 hour",
    TempoGrafico.H4: "4 hours",
    TempoGrafico.D1: "1 day",
    TempoGrafico.W1: "7 days",
}


class ConsultasMercado(Protocol):
    async def candles(
        self, simbolo: str, tg: TempoGrafico, ate: InstanteMs, limite: int
    ) -> list[Candle]:
        """Candles fechados com abertura ``< ate``, em ordem crescente, no máximo ``limite``.

        A janela de ``limite`` períodos termina no último dado existente antes de ``ate``:
        com a coleta parada, o gráfico ainda mostra o histórico. Lacunas reduzem a contagem.
        """
        ...

    async def qualidade_recentes(self, limite: int) -> list[EventoQualidade]:
        """Eventos de qualidade de dados, do mais novo para o mais antigo."""
        ...


def _limite_superior(ate: InstanteMs, tg: TempoGrafico) -> InstanteMs:
    """Fim (exclusivo) do último bloco com abertura ``< ate``."""
    return abertura_candle(max(ate - 1, 0), tg) + tg.duracao_ms


class ConsultasMercadoMemoria:
    def __init__(self, repo: RepositorioCandlesMemoria) -> None:
        self._repo = repo

    async def candles(
        self, simbolo: str, tg: TempoGrafico, ate: InstanteMs, limite: int
    ) -> list[Candle]:
        anteriores = await self._repo.listar(
            simbolo, IntervaloColeta.M1, 0, _limite_superior(ate, tg)
        )
        if not anteriores:
            return []
        fim = abertura_candle(anteriores[-1].abertura, tg) + tg.duracao_ms
        inicio = max(0, fim - limite * tg.duracao_ms)
        velas = [c for c in anteriores if c.abertura >= inicio]
        if tg is not TempoGrafico.M1:
            velas = agregar(velas, tg)
        return [c for c in velas if c.abertura < ate][-limite:]

    async def qualidade_recentes(self, limite: int) -> list[EventoQualidade]:
        return list(reversed(self._repo.todos_eventos_qualidade()))[:limite]


class ConsultasMercadoPg:  # pragma: no cover - testado na integração
    def __init__(self, engine: Any) -> None:
        self._engine = engine

    async def candles(
        self, simbolo: str, tg: TempoGrafico, ate: InstanteMs, limite: int
    ) -> list[Candle]:
        from sqlalchemy import func, select, text

        from sinais.persistencia.repositorio_pg import _candle
        from sinais.persistencia.tabelas import candles_1m

        if tg is TempoGrafico.M1:
            t = candles_1m
            stmt = (
                select(t)
                .where(t.c.simbolo == simbolo, t.c.abertura < para_datetime(ate))
                .order_by(t.c.abertura.desc())
                .limit(limite)
            )
            async with self._engine.connect() as conn:
                linhas = (await conn.execute(stmt)).all()
            return [_candle(linha, _M) for linha in reversed(linhas)]
        t = candles_1m
        async with self._engine.connect() as conn:
            ultima = await conn.scalar(
                select(func.max(t.c.abertura)).where(
                    t.c.simbolo == simbolo,
                    t.c.abertura < para_datetime(_limite_superior(ate, tg)),
                )
            )
        if ultima is None:
            return []
        fim = abertura_candle(de_datetime(ultima), tg) + tg.duracao_ms
        inicio = max(0, fim - limite * tg.duracao_ms)
        sql = text(
            f"""
            SELECT time_bucket(INTERVAL '{_INTERVALOS_SQL[tg]}', abertura) AS abertura,
                   :simbolo AS simbolo,
                   first(abertura_preco, abertura) AS abertura_preco,
                   max(maxima) AS maxima,
                   min(minima) AS minima,
                   last(fechamento, abertura) AS fechamento,
                   sum(volume) AS volume,
                   sum(volume_cotacao) AS volume_cotacao,
                   sum(negocios)::int AS negocios,
                   sum(volume_compra_agressora) AS volume_compra_agressora,
                   'agregado' AS fonte
            FROM candles_1m
            WHERE simbolo = :simbolo AND abertura >= :inicio AND abertura < :fim
            GROUP BY 1
            HAVING count(*) = :minutos
            ORDER BY 1 DESC
            LIMIT :limite
            """  # noqa: S608 - o intervalo vem de um dicionário fixo, nunca da requisição
        )
        params = {
            "simbolo": simbolo,
            "inicio": para_datetime(inicio),
            "fim": para_datetime(fim),
            "minutos": tg.duracao_ms // _M,
            "limite": limite,
        }
        async with self._engine.connect() as conn:
            linhas = (await conn.execute(sql, params)).all()
        return [
            c
            for c in (_candle(linha, tg.duracao_ms) for linha in reversed(linhas))
            if c.abertura < ate
        ]

    async def qualidade_recentes(self, limite: int) -> list[EventoQualidade]:
        from sqlalchemy import select

        from sinais.persistencia.tabelas import eventos_qualidade as t

        stmt = (
            select(t.c.simbolo, t.c.intervalo, t.c.inicio, t.c.fim, t.c.tipo)
            .order_by(t.c.id.desc())
            .limit(limite)
        )
        async with self._engine.connect() as conn:
            linhas = (await conn.execute(stmt)).all()
        return [(s, i, de_datetime(a), de_datetime(b), tp) for s, i, a, b, tp in linhas]
