import asyncio
from dataclasses import replace

import pytest

from sinais.contas.modelos import Modo, StatusUsuario
from sinais.contas.seguranca import hash_token
from sinais.contas.servico import ErroConta, ParametrosContas, ResultadoLogin

from .dubles import SO_BTC, T0, Ambiente, D, M, admin, ambiente, cliente, codigo_totp


async def entrar(
    amb: Ambiente, email: str = "ana@exemplo.com", senha: str = "senha-forte-123"
) -> ResultadoLogin:
    return await amb.servico.login(email, senha, None, "ip", "ua")


def test_token_desconhecido_401() -> None:
    async def caso() -> None:
        amb = ambiente()
        for token in (None, "", "inventado"):
            with pytest.raises(ErroConta) as e:
                await amb.servico.autenticar(token)
            assert (e.value.status, e.value.codigo) == (401, "sessao_invalida")

    asyncio.run(caso())


def test_sessao_expira_por_duracao_e_por_ociosidade() -> None:
    async def caso() -> None:
        amb = ambiente(ParametrosContas(sessao_duracao_ms=2 * D, sessao_ociosa_ms=D))
        await cliente(amb, fim=T0 + 90 * D)
        r = await entrar(amb)
        amb.relogio.avancar(D - M)
        await amb.servico.autenticar(r.token)  # toca último uso
        amb.relogio.avancar(D - M)
        await amb.servico.autenticar(r.token)
        amb.relogio.avancar(D)  # passou da duração total
        with pytest.raises(ErroConta):
            await amb.servico.autenticar(r.token)
        r2 = await entrar(amb)
        amb.relogio.avancar(D + 1)  # ociosa
        with pytest.raises(ErroConta):
            await amb.servico.autenticar(r2.token)

    asyncio.run(caso())


def test_usuario_bloqueado_perde_sessao() -> None:
    async def caso() -> None:
        amb = ambiente()
        u = await cliente(amb)
        r = await entrar(amb)
        await amb.repo.salvar_usuario(replace(u, status=StatusUsuario.BLOQUEADO))
        with pytest.raises(ErroConta) as e:
            await amb.servico.autenticar(r.token)
        assert e.value.status == 401
        s = await amb.repo.sessao(hash_token(r.token))
        assert s is not None and s.revogada_em is not None

    asyncio.run(caso())


def test_logout_revoga_e_registra() -> None:
    async def caso() -> None:
        amb = ambiente()
        u = await cliente(amb)
        r = await entrar(amb)
        await amb.servico.logout(r.token, "ip", "ua")
        with pytest.raises(ErroConta):
            await amb.servico.autenticar(r.token)
        assert [a.evento for a in await amb.repo.listar_acessos(u.id, 10)] == ["logout", "login"]
        await amb.servico.logout("token-qualquer", "ip", "ua")  # idempotente

    asyncio.run(caso())


def test_assinatura_ativa_vencida_e_inexistente() -> None:
    async def caso() -> None:
        amb = ambiente()
        await cliente(amb, fim=T0 + D)
        await cliente(amb, email="sem@exemplo.com", recursos=None)
        r = await entrar(amb)
        ctx = await amb.servico.autenticar(r.token)
        assert ctx.status_assinatura == "ativa"
        amb.servico.exigir_assinatura(ctx)
        amb.relogio.avancar(D)  # vence exatamente agora
        ctx = await amb.servico.autenticar(r.token)
        assert ctx.status_assinatura == "vencida"
        with pytest.raises(ErroConta) as e:
            amb.servico.exigir_assinatura(ctx)
        assert (e.value.status, e.value.codigo) == (402, "assinatura_vencida")
        r2 = await entrar(amb, "sem@exemplo.com")
        ctx2 = await amb.servico.autenticar(r2.token)
        assert ctx2.assinatura is None and ctx2.status_assinatura == "vencida"
        with pytest.raises(ErroConta) as e:
            amb.servico.exigir_assinatura(ctx2)
        assert e.value.status == 402

    asyncio.run(caso())


def test_admin_dispensado_de_assinatura() -> None:
    async def caso() -> None:
        amb = ambiente()
        await admin(amb)
        r = await amb.servico.login(
            "admin@exemplo.com", "senha-admin-123", codigo_totp(T0), "i", "u"
        )
        ctx = await amb.servico.autenticar(r.token)
        amb.servico.exigir_assinatura(ctx)
        amb.servico.exigir_admin(ctx)

    asyncio.run(caso())


def test_cliente_nao_e_admin() -> None:
    async def caso() -> None:
        amb = ambiente()
        await cliente(amb)
        ctx = await amb.servico.autenticar((await entrar(amb)).token)
        with pytest.raises(ErroConta) as e:
            amb.servico.exigir_admin(ctx)
        assert (e.value.status, e.value.codigo) == (403, "sem_permissao")

    asyncio.run(caso())


def test_csrf_exige_cabecalho_igual_ao_cookie_e_a_sessao() -> None:
    async def caso() -> None:
        amb = ambiente()
        await cliente(amb)
        await cliente(amb, email="bia@exemplo.com")
        r = await entrar(amb)
        outro = await entrar(amb, "bia@exemplo.com")
        ctx = await amb.servico.autenticar(r.token)
        amb.servico.verificar_csrf(ctx, r.csrf, r.csrf)
        for cab, cookie in (
            (None, r.csrf),
            (r.csrf, None),
            ("x", "x"),
            (r.csrf, "y"),
            (outro.csrf, outro.csrf),
        ):
            with pytest.raises(ErroConta) as e:
                amb.servico.verificar_csrf(ctx, cab, cookie)
            assert (e.value.status, e.value.codigo) == (403, "csrf_invalido")

    asyncio.run(caso())


def test_trocar_senha_derruba_outras_sessoes() -> None:
    async def caso() -> None:
        amb = ambiente(ParametrosContas(sessoes_simultaneas=2))
        await cliente(amb)
        a, b = await entrar(amb), await entrar(amb)
        ctx = await amb.servico.autenticar(b.token)
        with pytest.raises(ErroConta) as e:
            await amb.servico.trocar_senha(ctx, "errada-errada", "nova-senha-456")
        assert (e.value.status, e.value.codigo) == (422, "senha_atual_incorreta")
        with pytest.raises(ErroConta) as e:
            await amb.servico.trocar_senha(ctx, "senha-forte-123", "curta")
        assert (e.value.status, e.value.codigo) == (422, "senha_fraca")
        await amb.servico.trocar_senha(ctx, "senha-forte-123", "nova-senha-456")
        with pytest.raises(ErroConta):
            await amb.servico.autenticar(a.token)
        await amb.servico.autenticar(b.token)
        await amb.servico.logout(b.token, "ip", "ua")
        await entrar(amb, senha="nova-senha-456")

    asyncio.run(caso())


def test_preferencias_modo_avancado_exige_plano() -> None:
    async def caso() -> None:
        amb = ambiente()
        await cliente(amb, recursos=SO_BTC)
        await cliente(amb, email="full@exemplo.com")
        ctx = await amb.servico.autenticar((await entrar(amb)).token)
        with pytest.raises(ErroConta) as e:
            await amb.servico.preferencias(ctx, Modo.AVANCADO, None)
        assert (e.value.status, e.value.codigo) == (403, "recurso_nao_incluido")
        u = await amb.servico.preferencias(ctx, None, {"grafico": {"tg": "5m"}})
        assert u.layout == {"grafico": {"tg": "5m"}} and u.modo is Modo.ESSENCIAL
        with pytest.raises(ErroConta) as e:
            await amb.servico.preferencias(ctx, None, {"x": "a" * 70_000})
        assert (e.value.status, e.value.codigo) == (422, "layout_grande")
        ctx2 = await amb.servico.autenticar((await entrar(amb, "full@exemplo.com")).token)
        u2 = await amb.servico.preferencias(ctx2, Modo.AVANCADO, None)
        assert u2.modo is Modo.AVANCADO

    asyncio.run(caso())


def test_troca_de_senha_tem_limite_por_sessao() -> None:
    async def caso() -> None:
        amb = ambiente()
        await cliente(amb)
        ctx = await amb.servico.autenticar((await entrar(amb)).token)
        for _ in range(5):
            with pytest.raises(ErroConta) as e:
                await amb.servico.trocar_senha(ctx, "errada-errada", "nova-senha-456")
            assert e.value.status == 422
        with pytest.raises(ErroConta) as e:
            await amb.servico.trocar_senha(ctx, "senha-forte-123", "nova-senha-456")
        assert (e.value.status, e.value.codigo) == (429, "muitas_tentativas")

    asyncio.run(caso())


def test_layout_profundo_demais_da_422() -> None:
    async def caso() -> None:
        amb = ambiente()
        await cliente(amb)
        ctx = await amb.servico.autenticar((await entrar(amb)).token)
        fundo: dict[str, object] = {}
        atual = fundo
        for _ in range(5000):
            novo: dict[str, object] = {}
            atual["a"] = novo
            atual = novo
        with pytest.raises(ErroConta) as e:
            await amb.servico.preferencias(ctx, None, fundo)
        assert (e.value.status, e.value.codigo) == (422, "layout_invalido")

    asyncio.run(caso())
