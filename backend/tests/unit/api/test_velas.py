"""Gestor das velas em formação na API: carga do banco, ticks, vazão de 100 ms e fechamento."""

import asyncio
from decimal import Decimal

from sinais.api.velas import GestorVelas
from sinais.api.ws_canais import Distribuidor, interpretar
from sinais.core.tempo import RelogioFixo
from sinais.dados.modelos import Candle
from sinais.dados.vela_formacao import Negocio
from sinais.eventos.contratos import evento_candle_fechado
from sinais.persistencia.memoria import RepositorioCandlesMemoria

M = 60_000
T9 = 1795597200000  # quarta 09:00Z
D_ = Decimal


def vela(abertura: int, c: str, v: str = "1") -> Candle:
    p = D_(c)
    return Candle("BTCUSDT", M, abertura, p, p, p, p, D_(v), D_(0), 1, D_(0), "binance")


def neg(id_: int, t: int, preco: str) -> Negocio:
    return Negocio(id_, D_(preco), D_("1"), t, False)


async def montar(agora: int) -> tuple[GestorVelas, Distribuidor, RepositorioCandlesMemoria]:
    repo = RepositorioCandlesMemoria()
    await repo.inserir([vela(T9 - M, "90"), vela(T9, "100", "2"), vela(T9 + M, "101", "3")])
    d = Distribuidor()
    g = GestorVelas(["BTCUSDT"], repo, RelogioFixo(agora), d)
    await g.carregar()
    return g, d, repo


def test_tick_atualiza_todos_os_tempos_com_vazao_coalescida() -> None:
    async def caso() -> None:
        g, d, _ = await montar(T9 + 2 * M + 5000)
        a = d.novo_assinante()
        for canal in ("candles:BTCUSDT:1m", "candles:BTCUSDT:5m", "preco:BTCUSDT"):
            d.assinar(a, canal)
        for i, p in enumerate(("102", "105", "103")):
            g.ao_negocio("BTCUSDT", neg(i + 1, T9 + 2 * M + 1000 * (i + 6), p))
        saida = dict(g.drenar())
        assert set(saida) == {"candles:BTCUSDT:1m", "candles:BTCUSDT:5m", "preco:BTCUSDT"}
        assert saida["candles:BTCUSDT:1m"] == {
            "t": T9 + 2 * M,
            "o": "102",
            "h": "105",
            "l": "102",
            "c": "103",
            "v": "3",
            "fechado": False,
        }
        # 5m = minutos oficiais 09:00 e 09:01 do banco + negócios de 09:02
        assert saida["candles:BTCUSDT:5m"] == {
            "t": T9,
            "o": "100",
            "h": "105",
            "l": "100",
            "c": "103",
            "v": "8",
            "fechado": False,
        }
        assert saida["preco:BTCUSDT"] == {"preco": "103", "t": T9 + 2 * M + 8000}
        assert g.drenar() == []  # nada novo: nada sai

    asyncio.run(caso())


def test_so_calcula_canais_com_assinantes() -> None:
    async def caso() -> None:
        g, _, _ = await montar(T9 + 2 * M)
        g.ao_negocio("BTCUSDT", neg(1, T9 + 2 * M, "102"))
        assert g.drenar() == []

    asyncio.run(caso())


def test_snapshot_na_assinatura() -> None:
    async def caso() -> None:
        g, _, _ = await montar(T9 + 2 * M)
        assert g.snapshot("candles:BTCUSDT:15m") is None
        g.ao_negocio("BTCUSDT", neg(1, T9 + 2 * M + 1, "99"))
        assert g.snapshot("candles:BTCUSDT:15m") == {
            "t": T9,
            "o": "100",
            "h": "101",
            "l": "99",
            "c": "99",
            "v": "6",
            "fechado": False,
        }
        assert g.snapshot("preco:BTCUSDT") == {"preco": "99", "t": T9 + 2 * M + 1}
        assert g.snapshot("analise:BTCUSDT") is None

    asyncio.run(caso())


def test_fechamento_oficial_reconcilia_e_lacuna_recarrega_do_banco() -> None:
    async def caso() -> None:
        g, d, repo = await montar(T9 + 2 * M)
        a = d.novo_assinante()
        d.assinar(a, "candles:BTCUSDT:5m")
        g.ao_negocio("BTCUSDT", neg(1, T9 + 2 * M + 1, "102"))
        g.ao_negocio("BTCUSDT", neg(2, T9 + 3 * M + 1, "104"))
        # fechamento oficial de 09:02 com valores diferentes do parcial
        oficial = vela(T9 + 2 * M, "110", "9")
        await repo.inserir([oficial])
        await g.ao_fechado(evento_candle_fechado(oficial))
        assert dict(g.drenar())["candles:BTCUSDT:5m"]["v"] == "15"  # 2+3+9 oficiais + 1 negócio
        # chega o de 09:04 sem o de 09:03: recarrega do banco
        await repo.inserir([vela(T9 + 3 * M, "104", "1"), vela(T9 + 4 * M, "105", "1")])
        await g.ao_fechado(evento_candle_fechado(vela(T9 + 4 * M, "105", "1")))
        g.ao_negocio("BTCUSDT", neg(3, T9 + 5 * M, "106"))
        assert dict(g.drenar())["candles:BTCUSDT:5m"] == {
            "t": T9 + 5 * M,
            "o": "106",
            "h": "106",
            "l": "106",
            "c": "106",
            "v": "1",
            "fechado": False,
        }
        assert g.vela_oficial_ok("BTCUSDT")

    asyncio.run(caso())


def test_canal_preco_no_websocket() -> None:
    acao, canal = interpretar('{"acao": "assinar", "canal": "preco:BTCUSDT"}', ("BTCUSDT",))
    assert (acao, canal.tipo, canal.simbolo, canal.nome) == (
        "assinar",
        "preco",
        "BTCUSDT",
        "preco:BTCUSDT",
    )


def test_primeiro_fechamento_com_banco_vazio_na_carga_recarrega_o_periodo() -> None:
    async def caso() -> None:
        repo = RepositorioCandlesMemoria()
        d = Distribuidor()
        g = GestorVelas(["BTCUSDT"], repo, RelogioFixo(T9 + 2 * M + 10), d)
        await g.carregar()  # banco ainda vazio (backfill em andamento)
        a = d.novo_assinante()
        d.assinar(a, "candles:BTCUSDT:1h")
        g.ao_negocio("BTCUSDT", neg(1, T9 + 2 * M + 5, "102"))
        await repo.inserir([vela(T9, "100", "2"), vela(T9 + M, "101", "3")])
        primeiro = vela(T9 + 2 * M, "103", "4")
        await repo.inserir([primeiro])
        await g.ao_fechado(evento_candle_fechado(primeiro))
        g.ao_negocio("BTCUSDT", neg(2, T9 + 3 * M + 5, "99"))
        h1 = dict(g.drenar())["candles:BTCUSDT:1h"]
        # 09:00 + 09:01 + 09:02 oficiais do banco + negócio de 09:03
        assert (h1["t"], h1["o"], h1["h"], h1["l"], h1["c"], h1["v"]) == (
            T9,
            "100",
            "103",
            "99",
            "99",
            "10",
        )
        assert g.vela_oficial_ok("BTCUSDT")

    asyncio.run(caso())


def test_banco_atrasado_em_relacao_ao_evento_mantem_o_oficial_e_tenta_de_novo() -> None:
    async def caso() -> None:
        repo = RepositorioCandlesMemoria()
        d = Distribuidor()
        g = GestorVelas(["BTCUSDT"], repo, RelogioFixo(T9 + 2 * M + 10), d)
        await g.carregar()
        a = d.novo_assinante()
        d.assinar(a, "candles:BTCUSDT:1h")
        await repo.inserir([vela(T9, "100", "2"), vela(T9 + M, "101", "3")])
        # o evento de 09:02 chega antes de o banco ter a linha (réplica atrasada)
        await g.ao_fechado(evento_candle_fechado(vela(T9 + 2 * M, "103", "4")))
        g.ao_negocio("BTCUSDT", neg(1, T9 + 3 * M + 5, "104"))
        h1 = dict(g.drenar())["candles:BTCUSDT:1h"]
        assert (h1["o"], h1["h"], h1["c"], h1["v"]) == ("100", "104", "104", "10")
        assert g.vela_oficial_ok("BTCUSDT")

        # banco sem nada: o oficial vale, mas a próxima chegada recarrega de novo
        g2 = GestorVelas(["BTCUSDT"], RepositorioCandlesMemoria(), RelogioFixo(T9 + 2 * M), d)
        await g2.carregar()
        await g2.ao_fechado(evento_candle_fechado(vela(T9 + 2 * M, "103", "4")))
        assert not g2.vela_oficial_ok("BTCUSDT")

    asyncio.run(caso())
