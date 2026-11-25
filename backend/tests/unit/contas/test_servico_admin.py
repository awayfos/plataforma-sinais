import asyncio
import json

import pytest

from sinais.contas.admin import ServicoAdmin
from sinais.contas.contexto import Contexto
from sinais.contas.modelos import ItemPayout, Recursos, StatusUsuario
from sinais.contas.servico import ErroConta

from .dubles import SO_BTC, T0, TODOS, Ambiente, D, admin, ambiente, cliente, codigo_totp, plano


async def preparar() -> tuple[Ambiente, ServicoAdmin, Contexto]:
    amb = ambiente()
    await admin(amb)
    r = await amb.servico.login("admin@exemplo.com", "senha-admin-123", codigo_totp(T0), "i", "u")
    ctx = await amb.servico.autenticar(r.token)
    return amb, ServicoAdmin(amb.servico, ("BTCUSDT", "ETHUSDT")), ctx


def test_criar_usuario_com_plano_e_vencimento() -> None:
    async def caso() -> None:
        amb, adm, ctx = await preparar()
        p = await plano(amb, TODOS)
        f = await adm.criar_usuario(ctx, " Bia@Exemplo.com ", "Bia", "temporaria-123", p.id, None)
        assert f.usuario.email == "bia@exemplo.com" and f.usuario.papel == "cliente"
        assert f.assinatura is not None and f.assinatura.fim == T0 + 30 * D
        assert f.plano == p
        f2 = await adm.criar_usuario(
            ctx, "c@exemplo.com", "C", "temporaria-123", "Completo", T0 + D
        )
        assert f2.assinatura is not None and f2.assinatura.fim == T0 + D
        r = await amb.servico.login("bia@exemplo.com", "temporaria-123", None, "i", "u")
        amb.servico.exigir_assinatura(await amb.servico.autenticar(r.token))

    asyncio.run(caso())


def test_criar_usuario_valida_entradas() -> None:
    async def caso() -> None:
        amb, adm, ctx = await preparar()
        p = await plano(amb, TODOS)
        casos = [
            (("bia@exemplo.com", "Bia", "curta", p.id, None), 422, "senha_fraca"),
            (("sem-arroba", "Bia", "temporaria-123", p.id, None), 422, "email_invalido"),
            (("bia@exemplo.com", "Bia", "temporaria-123", 999, None), 422, "plano_inexistente"),
            (
                ("bia@exemplo.com", "Bia", "temporaria-123", p.id, T0 - 1),
                422,
                "vencimento_invalido",
            ),
            (("admin@exemplo.com", "X", "temporaria-123", p.id, None), 409, "email_em_uso"),
        ]
        for args, status, codigo in casos:
            with pytest.raises(ErroConta) as e:
                await adm.criar_usuario(ctx, *args)
            assert (e.value.status, e.value.codigo) == (status, codigo), args

    asyncio.run(caso())


def test_bloquear_revoga_sessoes_e_audita_sem_segredos() -> None:
    async def caso() -> None:
        amb, adm, ctx = await preparar()
        u = await cliente(amb)
        r = await amb.servico.login("ana@exemplo.com", "senha-forte-123", None, "i", "u")
        f = await adm.editar_usuario(ctx, u.id, status=StatusUsuario.BLOQUEADO)
        assert f.usuario.status is StatusUsuario.BLOQUEADO
        with pytest.raises(ErroConta):
            await amb.servico.autenticar(r.token)
        reg = (await adm.auditoria(10))[0]
        assert (reg.acao, reg.alvo, reg.admin_id) == (
            "usuario.editar",
            f"usuario:{u.id}",
            ctx.usuario.id,
        )
        assert reg.antes is not None and reg.antes["status"] == "ativo"
        assert reg.depois is not None and reg.depois["status"] == "bloqueado"
        texto = json.dumps([reg.antes, reg.depois])
        assert "senha" not in texto and "h:" not in texto and "totp" not in texto

    asyncio.run(caso())


def test_senha_temporaria_nova_derruba_sessoes() -> None:
    async def caso() -> None:
        amb, adm, ctx = await preparar()
        u = await cliente(amb)
        r = await amb.servico.login("ana@exemplo.com", "senha-forte-123", None, "i", "u")
        await adm.editar_usuario(ctx, u.id, nome="Ana Paula", senha_temporaria="outra-senha-99")
        with pytest.raises(ErroConta):
            await amb.servico.autenticar(r.token)
        await amb.servico.login("ana@exemplo.com", "outra-senha-99", None, "i", "u")
        reg = (await adm.auditoria(10))[0]
        assert reg.depois is not None and reg.depois["senha_redefinida"] is True
        assert "outra-senha-99" not in json.dumps(reg.depois)

    asyncio.run(caso())


def test_editar_inexistente_e_a_si_mesmo() -> None:
    async def caso() -> None:
        _, adm, ctx = await preparar()
        with pytest.raises(ErroConta) as e:
            await adm.editar_usuario(ctx, 999, nome="X")
        assert (e.value.status, e.value.codigo) == (404, "usuario_inexistente")
        with pytest.raises(ErroConta) as e:
            await adm.editar_usuario(ctx, ctx.usuario.id, status=StatusUsuario.BLOQUEADO)
        assert (e.value.status, e.value.codigo) == (422, "acao_invalida")

    asyncio.run(caso())


def test_planos_criar_editar_validar() -> None:
    async def caso() -> None:
        _, adm, ctx = await preparar()
        p = await adm.criar_plano(ctx, "Básico", 30, 4900, SO_BTC, True)
        p2 = await adm.editar_plano(ctx, p.id, preco_centavos=5900, ativo=False)
        assert (p2.preco_centavos, p2.ativo, p2.recursos) == (5900, False, SO_BTC)
        assert await adm.listar_planos() == [p2]
        invalidos = [
            Recursos(("XRPUSDT",), ("1m",), False, False),
            Recursos(("BTCUSDT",), ("2m",), False, False),
        ]
        for rec in invalidos:
            with pytest.raises(ErroConta) as e:
                await adm.criar_plano(ctx, "X", 30, 1, rec, True)
            assert e.value.status == 422
        with pytest.raises(ErroConta) as e:
            await adm.criar_plano(ctx, "Y", 0, 1, SO_BTC, True)
        assert e.value.codigo == "plano_invalido"
        with pytest.raises(ErroConta) as e:
            await adm.criar_plano(ctx, "Básico", 30, 1, SO_BTC, True)
        assert (e.value.status, e.value.codigo) == (409, "plano_existente")
        with pytest.raises(ErroConta) as e:
            await adm.editar_plano(ctx, 999, ativo=True)
        assert e.value.status == 404
        assert [r.acao for r in await adm.auditoria(10)] == ["plano.editar", "plano.criar"]

    asyncio.run(caso())


def test_renovar_assinatura() -> None:
    async def caso() -> None:
        amb, adm, ctx = await preparar()
        u = await cliente(amb, fim=T0 + D)
        p = await plano(amb, TODOS)
        a = await adm.criar_assinatura(ctx, u.id, p.id, T0, T0 + 60 * D)
        assert (await amb.repo.assinatura_atual(u.id, T0 + 2 * D)) == a
        for args, codigo in (
            ((999, p.id, T0, T0 + D), "usuario_inexistente"),
            ((u.id, 999, T0, T0 + D), "plano_inexistente"),
            ((u.id, p.id, T0 + D, T0), "periodo_invalido"),
        ):
            with pytest.raises(ErroConta) as e:
                await adm.criar_assinatura(ctx, *args)
            assert e.value.codigo == codigo
        assert (await adm.auditoria(1))[0].acao == "assinatura.criar"

    asyncio.run(caso())


def test_payout_exnova_substitui_e_valida() -> None:
    async def caso() -> None:
        _, adm, ctx = await preparar()
        itens = [ItemPayout("ETHUSDT", "5m", 0.86), ItemPayout("BTCUSDT", "1m", 0.88)]
        assert await adm.substituir_payouts(ctx, itens) == sorted(itens, key=lambda i: i.simbolo)
        assert await adm.payouts() == [itens[1], itens[0]]
        ruins = [
            [ItemPayout("XRPUSDT", "1m", 0.8)],
            [ItemPayout("BTCUSDT", "2m", 0.8)],
            [ItemPayout("BTCUSDT", "1m", 0.0)],
            [ItemPayout("BTCUSDT", "1m", 1.5)],
            [ItemPayout("BTCUSDT", "1m", 0.8), ItemPayout("BTCUSDT", "1m", 0.9)],
        ]
        for r in ruins:
            with pytest.raises(ErroConta) as e:
                await adm.substituir_payouts(ctx, r)
            assert (e.value.status, e.value.codigo) == (422, "payout_invalido"), r
        assert (await adm.auditoria(1))[0].acao == "payout.substituir"

    asyncio.run(caso())


def test_listar_usuarios_traz_assinatura_e_acessos() -> None:
    async def caso() -> None:
        amb, adm, ctx = await preparar()
        u = await cliente(amb)
        await amb.servico.login("ana@exemplo.com", "senha-forte-123", None, "i", "u")
        fichas = await adm.listar_usuarios("ana", None)
        assert [f.usuario.id for f in fichas] == [u.id]
        assert fichas[0].assinatura is not None and fichas[0].plano is not None
        assert [a.evento for a in await adm.acessos(u.id, 10)] == ["login"]

    asyncio.run(caso())
