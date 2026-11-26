"""Consultas de leitura para a API: candles do gráfico e eventos de qualidade recentes.

Tempos gráficos maiores que 1m são agregados a partir de ``candles_1m`` com os minutos que
existem no período, e só períodos já fechados (fim <= agora). Uma lacuna na coleta não some
com o candle de 1d ou 1w inteiro: ele é montado com o que há (como faz a Binance). A conferência
contra os klines oficiais continua em ``sinais.dados.conferencia``.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Protocol

from sinais.core.dominio import TempoGrafico, abertura_candle
from sinais.core.tempo import InstanteMs, de_datetime, para_datetime
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
        self, simbolo: str, tg: TempoGrafico, ate: InstanteMs, limite: int, agora: InstanteMs
    ) -> list[Candle]:
        """Candles fechados com abertura ``< ate``, em ordem crescente, no máximo ``limite``.

        A janela de ``limite`` períodos termina no último dado existente antes de ``ate``:
        com a coleta parada, o gráfico ainda mostra o histórico. Lacunas reduzem a contagem.
        """
        ...

    async def qualidade_recentes(self, limite: int) -> list[EventoQualidade]:
        """Eventos de qualidade de dados, do mais novo para o mais antigo."""
        ...


def _limite_superior(ate: InstanteMs, tg: TempoGrafico, agora: InstanteMs) -> InstanteMs:
    """Fim (exclusivo) dos minutos usados: blocos com abertura ``< ate`` e já fechados."""
    fim = abertura_candle(max(ate - 1, 0), tg) + tg.duracao_ms
    return min(fim, abertura_candle(agora, tg))


def _somar(bloco: list[Candle], tg: TempoGrafico, abertura: InstanteMs) -> Candle:
    return Candle(
        simbolo=bloco[0].simbolo,
        intervalo_ms=tg.duracao_ms,
        abertura=abertura,
        abertura_preco=bloco[0].abertura_preco,
        maxima=max(c.maxima for c in bloco),
        minima=min(c.minima for c in bloco),
        fechamento=bloco[-1].fechamento,
        volume=sum((c.volume for c in bloco), start=Decimal(0)),
        volume_cotacao=sum((c.volume_cotacao for c in bloco), start=Decimal(0)),
        negocios=sum(c.negocios for c in bloco),
        volume_compra_agressora=sum((c.volume_compra_agressora for c in bloco), start=Decimal(0)),
        fonte="agregado",
    )


class ConsultasMercadoMemoria:
    def __init__(self, repo: RepositorioCandlesMemoria) -> None:
        self._repo = repo

    async def candles(
        self, simbolo: str, tg: TempoGrafico, ate: InstanteMs, limite: int, agora: InstanteMs
    ) -> list[Candle]:
        # Em 1m todo candle gravado já fechou; nos maiores, só períodos com fim <= agora.
        fim_dados = ate if tg is TempoGrafico.M1 else _limite_superior(ate, tg, agora)
        anteriores = await self._repo.listar(simbolo, IntervaloColeta.M1, 0, fim_dados)
        if not anteriores:
            return []
        fim = abertura_candle(anteriores[-1].abertura, tg) + tg.duracao_ms
        inicio = max(0, fim - limite * tg.duracao_ms)
        velas = [c for c in anteriores if c.abertura >= inicio]
        if tg is not TempoGrafico.M1:
            blocos: dict[int, list[Candle]] = {}
            for c in velas:
                blocos.setdefault(abertura_candle(c.abertura, tg), []).append(c)
            velas = [_somar(b, tg, ab) for ab, b in sorted(blocos.items())]
        return [c for c in velas if c.abertura < ate][-limite:]

    async def qualidade_recentes(self, limite: int) -> list[EventoQualidade]:
        return list(reversed(self._repo.todos_eventos_qualidade()))[:limite]


class ConsultasMercadoPg:  # pragma: no cover - testado na integração
    def __init__(self, engine: Any) -> None:
        self._engine = engine

    async def candles(
        self, simbolo: str, tg: TempoGrafico, ate: InstanteMs, limite: int, agora: InstanteMs
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
                    t.c.abertura < para_datetime(_limite_superior(ate, tg, agora)),
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
            ORDER BY 1 DESC
            LIMIT :limite
            """  # noqa: S608 - o intervalo vem de um dicionário fixo, nunca da requisição
        )
        params = {
            "simbolo": simbolo,
            "inicio": para_datetime(inicio),
            "fim": para_datetime(fim),
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
