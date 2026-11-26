"""Requisições concorrentes não ressuscitam sessões nem desfazem bloqueios (revisão de
segurança do PR #14)."""

import asyncio

import pytest

from sinais.contas.modelos import Modo, StatusUsuario
from sinais.contas.seguranca import hash_token
from sinais.contas.servico import ErroConta

from .dubles import T0, M, admin, ambiente, ambiente_concorrente, cliente, codigo_totp

SENHA = "senha-forte-123"


def test_logins_simultaneos_com_limite_1_deixam_uma_sessao() -> None:
    async def caso() -> None:
        amb = ambiente_concorrente()
        u = await cliente(amb)
        await asyncio.gather(
            amb.servico.login("ana@exemplo.com", SENHA, None, "i1", "u"),
            amb.servico.login("ana@exemplo.com", SENHA, None, "i2", "u"),
        )
        assert len(await amb.repo.sessoes_ativas(u.id, T0)) == 1

    asyncio.run(caso())


def test_mesmo_totp_em_paralelo_so_entra_uma_vez() -> None:
    async def caso() -> tuple[object, ...]:
        amb = ambiente_concorrente()
        await admin(amb)
        codigo = codigo_totp(T0)
        return await asyncio.gather(
            amb.servico.login("admin@exemplo.com", "senha-admin-123", codigo, "i1", "u"),
            amb.servico.login("admin@exemplo.com", "senha-admin-123", codigo, "i2", "u"),
            return_exceptions=True,
        )

    resultados = asyncio.run(caso())
    erros = [r for r in resultados if isinstance(r, ErroConta)]
    assert len(erros) == 1 and erros[0].codigo == "totp_invalido"


def test_autenticar_nao_ressuscita_sessao_revogada_ao_mesmo_tempo() -> None:
    async def caso() -> None:
        amb = ambiente_concorrente()
        u = await cliente(amb)
        r = await amb.servico.login("ana@exemplo.com", SENHA, None, "i", "u")
        amb.relogio.avancar(2 * M)  # o autenticar vai gravar o último uso
        await asyncio.gather(
            amb.servico.autenticar(r.token),
            amb.repo.revogar_sessoes(u.id, amb.relogio.agora_ms(), "admin"),
            return_exceptions=True,
        )
        s = await amb.repo.sessao(hash_token(r.token))
        assert s is not None and s.revogada_em is not None
        with pytest.raises(ErroConta):
            await amb.servico.autenticar(r.token)

    asyncio.run(caso())


def test_preferencias_com_contexto_antigo_nao_desbloqueiam() -> None:
    async def caso() -> None:
        amb = ambiente()
        u = await cliente(amb)
        r = await amb.servico.login("ana@exemplo.com", SENHA, None, "i", "u")
        ctx = await amb.servico.autenticar(r.token)
        await amb.repo.atualizar_usuario(u.id, {"status": StatusUsuario.BLOQUEADO})
        await amb.servico.preferencias(ctx, Modo.AVANCADO, {"a": 1})
        lido = await amb.repo.usuario_por_id(u.id)
        assert lido is not None and lido.status is StatusUsuario.BLOQUEADO

    asyncio.run(caso())


def test_trocar_senha_com_contexto_antigo_nao_desbloqueia() -> None:
    async def caso() -> None:
        amb = ambiente()
        u = await cliente(amb)
        ctx = await amb.servico.autenticar(
            (await amb.servico.login("ana@exemplo.com", SENHA, None, "i", "u")).token
        )
        await amb.repo.atualizar_usuario(u.id, {"status": StatusUsuario.BLOQUEADO})
        await amb.servico.trocar_senha(ctx, SENHA, "nova-senha-456")
        lido = await amb.repo.usuario_por_id(u.id)
        assert lido is not None and lido.status is StatusUsuario.BLOQUEADO

    asyncio.run(caso())
