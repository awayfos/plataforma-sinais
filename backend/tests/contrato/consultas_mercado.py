"""Contrato de ``ConsultasMercado`` (candles para o gráfico e qualidade recente)."""

import asyncio
from collections.abc import Awaitable, Callable

from sinais.core.dominio import TempoGrafico
from sinais.dados.modelos import IntervaloColeta
from sinais.dados.qualidade import Lacuna
from sinais.persistencia.consultas_mercado import ConsultasMercado
from sinais.persistencia.repositorio import RepositorioCandles

from .repositorio_candles import T0, M, vela

type FabricaConsultas = Callable[[], Awaitable[tuple[RepositorioCandles, ConsultasMercado]]]


def candles_1m_antes_de_ate_em_ordem(fabrica: FabricaConsultas) -> None:
    async def caso() -> None:
        repo, c = await fabrica()
        await repo.inserir([vela(i) for i in range(10)])
        lidos = await c.candles("BTCUSDT", TempoGrafico.M1, T0 + 5 * M, 3, T0 + 20 * M)
        assert [x.abertura for x in lidos] == [T0 + 2 * M, T0 + 3 * M, T0 + 4 * M]
        assert lidos[0] == vela(2)
        assert await c.candles("ETHUSDT", TempoGrafico.M1, T0 + 5 * M, 3, T0 + 20 * M) == []

    asyncio.run(caso())


def agregados_com_minutos_disponiveis_e_so_periodos_fechados(fabrica: FabricaConsultas) -> None:
    async def caso() -> None:
        repo, c = await fabrica()
        velas = [vela(i, preco=str(100 + i)) for i in range(15) if i != 7]  # falta o minuto 7
        await repo.inserir(velas)
        agora = T0 + 15 * M
        lidos = await c.candles("BTCUSDT", TempoGrafico.M5, T0 + 60 * M, 10, agora)
        assert [x.abertura for x in lidos] == [T0, T0 + 5 * M, T0 + 10 * M]
        b = lidos[0]
        assert b.intervalo_ms == 5 * M
        assert (b.abertura_preco, b.fechamento) == (velas[0].abertura_preco, velas[4].fechamento)
        assert b.maxima == max(v.maxima for v in velas[:5])
        assert b.minima == min(v.minima for v in velas[:5])
        assert b.volume == sum(v.volume for v in velas[:5])
        assert b.volume_compra_agressora == sum(v.volume_compra_agressora for v in velas[:5])
        # o bloco com lacuna (minuto 7) é agregado com os 4 minutos que existem
        lacuna = lidos[1]
        assert lacuna.volume == sum(v.volume for v in velas[5:9])
        assert lacuna.fechamento == velas[8].fechamento  # minuto 9
        # período ainda aberto não sai
        abertos = await c.candles("BTCUSDT", TempoGrafico.M5, T0 + 60 * M, 10, T0 + 14 * M)
        assert [x.abertura for x in abertos] == [T0, T0 + 5 * M]
        # "ate" corta pela abertura do bloco: o bloco que abre em ate fica de fora
        ate = await c.candles("BTCUSDT", TempoGrafico.M5, T0 + 10 * M, 10, agora)
        assert [x.abertura for x in ate] == [T0, T0 + 5 * M]
        um = await c.candles("BTCUSDT", TempoGrafico.M5, T0 + 60 * M, 1, agora)
        assert [x.abertura for x in um] == [T0 + 10 * M]

    asyncio.run(caso())


def qualidade_recentes_mais_novos_primeiro(fabrica: FabricaConsultas) -> None:
    async def caso() -> None:
        repo, c = await fabrica()
        await repo.registrar_qualidade("BTCUSDT", IntervaloColeta.M1, Lacuna(T0, T0 + M), "lacuna")
        await repo.registrar_qualidade("ETHUSDT", IntervaloColeta.S1, Lacuna(T0, T0 + 1000), "x")
        assert await c.qualidade_recentes(10) == [
            ("ETHUSDT", "1s", T0, T0 + 1000, "x"),
            ("BTCUSDT", "1m", T0, T0 + M, "lacuna"),
        ]
        assert len(await c.qualidade_recentes(1)) == 1

    asyncio.run(caso())


CASOS = [
    candles_1m_antes_de_ate_em_ordem,
    agregados_com_minutos_disponiveis_e_so_periodos_fechados,
    qualidade_recentes_mais_novos_primeiro,
]
