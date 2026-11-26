import asyncio

from sinais.contas.autorizacao import expiracoes_permitidas, pode_modo_avancado, pode_ver_ativo
from sinais.contas.contexto import Contexto

from .dubles import SO_BTC, T0, admin, ambiente, cliente, codigo_totp

TODAS = ("1m", "5m", "15m", "30m", "60m")


async def contextos() -> tuple[Contexto, Contexto, Contexto]:
    amb = ambiente()
    await cliente(amb, "full@exemplo.com")
    await cliente(amb, "btc@exemplo.com", recursos=SO_BTC)
    await admin(amb)
    s = amb.servico
    full = await s.autenticar(
        (await s.login("full@exemplo.com", "senha-forte-123", None, "i", "u")).token
    )
    btc = await s.autenticar(
        (await s.login("btc@exemplo.com", "senha-forte-123", None, "i", "u")).token
    )
    adm_login = await s.login("admin@exemplo.com", "senha-admin-123", codigo_totp(T0), "i", "u")
    return full, btc, await s.autenticar(adm_login.token)


def test_matriz_de_recursos_por_plano() -> None:
    full, btc, adm = asyncio.run(contextos())
    assert pode_ver_ativo(full, "ETHUSDT") and pode_ver_ativo(btc, "BTCUSDT")
    assert not pode_ver_ativo(btc, "ETHUSDT")
    assert pode_ver_ativo(adm, "ETHUSDT")
    assert expiracoes_permitidas(full, TODAS) == TODAS
    assert expiracoes_permitidas(btc, TODAS) == ("1m", "5m")
    assert expiracoes_permitidas(adm, TODAS) == TODAS
    assert pode_modo_avancado(full) and pode_modo_avancado(adm)
    assert not pode_modo_avancado(btc)
