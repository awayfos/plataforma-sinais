import asyncio

from sinais.contas.limites import ContadorMemoria, PoliticaLogin
from sinais.core.tempo import RelogioFixo

T0 = 1795575600000


def test_contador_janela_fixa_expira() -> None:
    async def caso() -> None:
        r = RelogioFixo(T0)
        c = ContadorMemoria(r)
        assert await c.incrementar("k", 60) == 1
        assert await c.incrementar("k", 60) == 2
        r.avancar(60_000)
        assert await c.incrementar("k", 60) == 1

    asyncio.run(caso())


def test_contador_gravar_ler_apagar_com_validade() -> None:
    async def caso() -> None:
        r = RelogioFixo(T0)
        c = ContadorMemoria(r)
        await c.gravar("b", "123", 10)
        assert await c.ler("b") == "123"
        r.avancar(10_000)
        assert await c.ler("b") is None
        await c.gravar("b", "1", 10)
        await c.apagar("b")
        assert await c.ler("b") is None

    asyncio.run(caso())


def test_bloqueio_progressivo_dobra_e_tem_teto() -> None:
    p = PoliticaLogin()
    assert [p.bloqueio_s(n) for n in (1, 4)] == [0, 0]
    assert [p.bloqueio_s(n) for n in (5, 6, 7)] == [60, 120, 240]
    assert p.bloqueio_s(50) == 1800
