"""Contrato de ``RepositorioContas``: os mesmos casos valem para o dublê e para o PostgreSQL."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import replace

import pytest

from sinais.contas.modelos import (
    ItemPayout,
    Modo,
    NovoPlano,
    NovoUsuario,
    Papel,
    Recursos,
    Sessao,
    StatusUsuario,
)
from sinais.contas.repositorio import ErroEmailDuplicado, RepositorioContas

T0 = 1795575600000
H = 3_600_000
D = 86_400_000

type Fabrica = Callable[[], Awaitable[RepositorioContas]]

RECURSOS = Recursos(
    ativos=("BTCUSDT", "ETHUSDT"),
    expiracoes=("1m", "5m"),
    modo_avancado=True,
    cursos=False,
)


def novo_usuario(email: str = "ana@exemplo.com", papel: Papel = Papel.CLIENTE) -> NovoUsuario:
    return NovoUsuario(email=email, nome="Ana", papel=papel, senha_hash="$argon2id$x", criado_em=T0)


def sessao(usuario_id: int, token_hash: str, criada: int = T0) -> Sessao:
    return Sessao(
        token_hash=token_hash,
        csrf_hash="c" + token_hash,
        usuario_id=usuario_id,
        criada_em=criada,
        ultimo_uso=criada,
        expira_em=criada + D,
        ip="10.0.0.1",
        user_agent="teste",
    )


def usuario_ida_e_volta(fabrica: Fabrica) -> None:
    async def caso() -> None:
        repo = await fabrica()
        u = await repo.criar_usuario(novo_usuario())
        assert u.id > 0
        assert u.status is StatusUsuario.ATIVO
        assert u.modo is Modo.ESSENCIAL
        assert u.layout == {}
        assert await repo.usuario_por_id(u.id) == u
        assert await repo.usuario_por_email("ana@exemplo.com") == u
        assert await repo.usuario_por_email("outra@exemplo.com") is None
        assert await repo.usuario_por_id(u.id + 999) is None

    asyncio.run(caso())


def email_duplicado_recusado(fabrica: Fabrica) -> None:
    async def caso() -> None:
        repo = await fabrica()
        await repo.criar_usuario(novo_usuario())
        with pytest.raises(ErroEmailDuplicado):
            await repo.criar_usuario(novo_usuario())

    asyncio.run(caso())


def salvar_usuario_grava_todos_os_campos(fabrica: Fabrica) -> None:
    async def caso() -> None:
        repo = await fabrica()
        u = await repo.criar_usuario(novo_usuario(papel=Papel.ADMIN))
        novo = replace(
            u,
            nome="Ana Maria",
            status=StatusUsuario.BLOQUEADO,
            senha_hash="$argon2id$y",
            totp_cifrado="cifra",
            totp_ultimo_passo=123,
            modo=Modo.AVANCADO,
            layout={"grafico": {"tg": "5m"}},
        )
        await repo.salvar_usuario(novo)
        assert await repo.usuario_por_id(u.id) == novo

    asyncio.run(caso())


def listar_usuarios_filtra(fabrica: Fabrica) -> None:
    async def caso() -> None:
        repo = await fabrica()
        a = await repo.criar_usuario(novo_usuario("ana@exemplo.com"))
        b = await repo.criar_usuario(novo_usuario("bruno@exemplo.com"))
        await repo.salvar_usuario(replace(b, status=StatusUsuario.BLOQUEADO, nome="Bruno"))
        assert [u.id for u in await repo.listar_usuarios(None, None)] == [a.id, b.id]
        assert [u.id for u in await repo.listar_usuarios("BRUNO", None)] == [b.id]
        assert [u.id for u in await repo.listar_usuarios(None, StatusUsuario.ATIVO)] == [a.id]
        assert await repo.listar_usuarios("ninguem", None) == []

    asyncio.run(caso())


def sessoes_criar_ler_revogar(fabrica: Fabrica) -> None:
    async def caso() -> None:
        repo = await fabrica()
        u = await repo.criar_usuario(novo_usuario())
        outro = await repo.criar_usuario(novo_usuario("b@exemplo.com"))
        await repo.criar_sessao(sessao(u.id, "h1", T0))
        await repo.criar_sessao(sessao(u.id, "h2", T0 + 1))
        await repo.criar_sessao(sessao(outro.id, "h3", T0))
        lida = await repo.sessao("h1")
        assert lida == sessao(u.id, "h1", T0)
        assert await repo.sessao("nao-existe") is None
        await repo.salvar_sessao(replace(sessao(u.id, "h1", T0), ultimo_uso=T0 + 5))
        assert (await repo.sessao("h1")).ultimo_uso == T0 + 5  # type: ignore[union-attr]
        ativas = await repo.sessoes_ativas(u.id, T0 + 10)
        assert [s.token_hash for s in ativas] == ["h1", "h2"]
        assert await repo.revogar_sessoes(u.id, T0 + 20, "teste", exceto="h2") == 1
        revogada = await repo.sessao("h1")
        assert revogada is not None and revogada.revogada_em == T0 + 20
        assert revogada.motivo_revogacao == "teste"
        assert [s.token_hash for s in await repo.sessoes_ativas(u.id, T0 + 30)] == ["h2"]
        assert await repo.sessoes_ativas(u.id, T0 + 2 * D) == []  # expiradas
        assert [s.token_hash for s in await repo.sessoes_ativas(outro.id, T0)] == ["h3"]

    asyncio.run(caso())


def planos_e_assinaturas(fabrica: Fabrica) -> None:
    async def caso() -> None:
        repo = await fabrica()
        u = await repo.criar_usuario(novo_usuario())
        p = await repo.criar_plano(NovoPlano("Mensal", 30, 9900, RECURSOS, True))
        assert await repo.plano(p.id) == p
        assert await repo.plano_por_nome("Mensal") == p
        assert await repo.plano(p.id + 99) is None
        p2 = replace(p, preco_centavos=12900, ativo=False)
        await repo.salvar_plano(p2)
        assert await repo.listar_planos() == [p2]
        assert await repo.assinatura_atual(u.id, T0) is None
        a1 = await repo.criar_assinatura(u.id, p.id, T0, T0 + 30 * D, "manual", T0)
        assert await repo.assinatura_atual(u.id, T0 + D) == a1
        # renovação: a de maior fim já iniciada vale
        a2 = await repo.criar_assinatura(u.id, p.id, T0 + D, T0 + 60 * D, "manual", T0 + D)
        assert await repo.assinatura_atual(u.id, T0 + 2 * D) == a2
        # assinatura futura ainda não vale
        await repo.criar_assinatura(u.id, p.id, T0 + 90 * D, T0 + 120 * D, "manual", T0)
        assert await repo.assinatura_atual(u.id, T0 + 2 * D) == a2
        # vencida continua sendo a atual (para mostrar "vencida")
        assert await repo.assinatura_atual(u.id, T0 + 70 * D) == a2

    asyncio.run(caso())


def acessos_e_auditoria(fabrica: Fabrica) -> None:
    async def caso() -> None:
        repo = await fabrica()
        u = await repo.criar_usuario(novo_usuario())
        v = await repo.criar_usuario(novo_usuario("v@exemplo.com"))
        await repo.registrar_acesso(u.id, "login", "1.2.3.4", "ua", T0)
        await repo.registrar_acesso(None, "login_falha", "1.2.3.4", "ua", T0 + 1)
        await repo.registrar_acesso(v.id, "logout", "5.6.7.8", "ua2", T0 + 2)
        todos = await repo.listar_acessos(None, 100)
        assert [(a.usuario_id, a.evento) for a in todos] == [
            (v.id, "logout"),
            (None, "login_falha"),
            (u.id, "login"),
        ]
        so_u = await repo.listar_acessos(u.id, 100)
        assert [(a.evento, a.ip, a.user_agent, a.t) for a in so_u] == [
            ("login", "1.2.3.4", "ua", T0)
        ]
        assert len(await repo.listar_acessos(None, 2)) == 2
        await repo.registrar_auditoria(u.id, "usuario.criar", "usuario:2", None, {"a": 1}, T0)
        await repo.registrar_auditoria(u.id, "plano.editar", "plano:1", {"b": 1}, {"b": 2}, T0 + 1)
        aud = await repo.listar_auditoria(100)
        assert [(r.acao, r.antes, r.depois) for r in aud] == [
            ("plano.editar", {"b": 1}, {"b": 2}),
            ("usuario.criar", None, {"a": 1}),
        ]
        assert aud[0].admin_id == u.id and aud[0].alvo == "plano:1" and aud[0].t == T0 + 1

    asyncio.run(caso())


def payouts_substituir_mantem_historico(fabrica: Fabrica) -> None:
    async def caso() -> None:
        repo = await fabrica()
        assert await repo.payouts_vigentes("exnova", T0) == []
        itens = [ItemPayout("BTCUSDT", "1m", 0.88), ItemPayout("ETHUSDT", "5m", 0.86)]
        await repo.substituir_payouts("exnova", itens, T0)
        assert await repo.payouts_vigentes("exnova", T0 + 1) == itens
        novos = [ItemPayout("BTCUSDT", "1m", 0.87)]
        await repo.substituir_payouts("exnova", novos, T0 + H)
        assert await repo.payouts_vigentes("exnova", T0 + H + 1) == novos
        # o payout vigente num instante passado continua consultável
        assert await repo.payouts_vigentes("exnova", T0 + 1) == itens

    asyncio.run(caso())


def tocar_e_revogar_sessao_nunca_ressuscitam(fabrica: Fabrica) -> None:
    async def caso() -> None:
        repo = await fabrica()
        u = await repo.criar_usuario(novo_usuario())
        await repo.criar_sessao(sessao(u.id, "h1", T0))
        assert await repo.tocar_sessao("h1", T0 + 5) is True
        assert (await repo.sessao("h1")).ultimo_uso == T0 + 5  # type: ignore[union-attr]
        assert await repo.revogar_sessao("h1", T0 + 6, "logout") is True
        assert await repo.revogar_sessao("h1", T0 + 7, "outro") is False
        assert await repo.tocar_sessao("h1", T0 + 8) is False
        s = await repo.sessao("h1")
        assert s is not None and (s.revogada_em, s.motivo_revogacao, s.ultimo_uso) == (
            T0 + 6,
            "logout",
            T0 + 5,
        )
        assert await repo.tocar_sessao("nao-existe", T0) is False

    asyncio.run(caso())


def revogar_excedentes_mantem_as_mais_novas(fabrica: Fabrica) -> None:
    async def caso() -> None:
        repo = await fabrica()
        u = await repo.criar_usuario(novo_usuario())
        for i, h in enumerate(("a", "b", "c")):
            await repo.criar_sessao(sessao(u.id, h, T0 + i))
        assert await repo.revogar_excedentes(u.id, 1, T0 + 10, "limite_sessoes") == 2
        assert [s.token_hash for s in await repo.sessoes_ativas(u.id, T0 + 10)] == ["c"]
        assert await repo.revogar_excedentes(u.id, 1, T0 + 11, "limite_sessoes") == 0

    asyncio.run(caso())


def passo_totp_so_avanca(fabrica: Fabrica) -> None:
    async def caso() -> None:
        repo = await fabrica()
        u = await repo.criar_usuario(novo_usuario(papel=Papel.ADMIN))
        assert await repo.registrar_passo_totp(u.id, 5) is True
        assert await repo.registrar_passo_totp(u.id, 5) is False
        assert await repo.registrar_passo_totp(u.id, 4) is False
        assert await repo.registrar_passo_totp(u.id, 6) is True
        assert (await repo.usuario_por_id(u.id)).totp_ultimo_passo == 6  # type: ignore[union-attr]

    asyncio.run(caso())


def atualizar_usuario_so_toca_as_colunas_pedidas(fabrica: Fabrica) -> None:
    async def caso() -> None:
        repo = await fabrica()
        u = await repo.criar_usuario(novo_usuario())
        outro = await repo.criar_usuario(novo_usuario("b@exemplo.com"))
        await repo.atualizar_usuario(u.id, {"status": StatusUsuario.BLOQUEADO})
        await repo.atualizar_usuario(u.id, {"senha_hash": "$argon2id$z", "nome": "Ana B"})
        lido = await repo.usuario_por_id(u.id)
        assert lido is not None
        assert (lido.status, lido.senha_hash, lido.nome) == (
            StatusUsuario.BLOQUEADO,
            "$argon2id$z",
            "Ana B",
        )
        with pytest.raises(ErroEmailDuplicado):
            await repo.atualizar_usuario(u.id, {"email": outro.email})
        with pytest.raises(ValueError):
            await repo.atualizar_usuario(u.id, {"id": 99})
        modo = await repo.atualizar_preferencias(u.id, Modo.AVANCADO, None)
        assert modo is not None and (modo.modo, modo.layout, modo.status) == (
            Modo.AVANCADO,
            {},
            StatusUsuario.BLOQUEADO,
        )
        lay = await repo.atualizar_preferencias(u.id, None, {"BTCUSDT": {"z": 1}})
        assert lay is not None and (lay.modo, lay.layout) == (Modo.AVANCADO, {"BTCUSDT": {"z": 1}})

    asyncio.run(caso())


def encerrar_assinatura_antes_do_fim(fabrica: Fabrica) -> None:
    async def caso() -> None:
        repo = await fabrica()
        u = await repo.criar_usuario(novo_usuario())
        p = await repo.criar_plano(NovoPlano("Mensal", 30, 9900, RECURSOS, True))
        a = await repo.criar_assinatura(u.id, p.id, T0, T0 + 30 * D, "manual", T0)
        assert await repo.assinatura(a.id) == a
        assert await repo.assinatura(a.id + 99) is None
        e = await repo.encerrar_assinatura(a.id, T0 + D)
        assert e is not None and e.fim == T0 + D
        assert await repo.assinatura_atual(u.id, T0 + D) == e
        again = await repo.encerrar_assinatura(a.id, T0 + 2 * D)  # já encerrada: não estica
        assert again is not None and again.fim == T0 + D
        assert await repo.encerrar_assinatura(a.id + 99, T0) is None

    asyncio.run(caso())


CASOS = [
    tocar_e_revogar_sessao_nunca_ressuscitam,
    revogar_excedentes_mantem_as_mais_novas,
    passo_totp_so_avanca,
    atualizar_usuario_so_toca_as_colunas_pedidas,
    encerrar_assinatura_antes_do_fim,
    usuario_ida_e_volta,
    email_duplicado_recusado,
    salvar_usuario_grava_todos_os_campos,
    listar_usuarios_filtra,
    sessoes_criar_ler_revogar,
    planos_e_assinaturas,
    acessos_e_auditoria,
    payouts_substituir_mantem_historico,
]
