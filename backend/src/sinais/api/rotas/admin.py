"""``/api/admin``: papel admin (sessão aberta com 2FA). Mutações exigem CSRF e são auditadas."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Query

from sinais.api import esquemas as e
from sinais.api.dependencias import Admin, AdminMutacao, Svc
from sinais.api.erros import RESPOSTAS_ERRO
from sinais.api.servicos import Servicos
from sinais.api.visoes import (
    acesso_saida,
    assinatura_saida,
    auditoria_saida,
    payout_saida,
    plano_saida,
    qualidade_saida,
    recursos_de,
    usuario_admin,
)
from sinais.contas.contexto import Contexto
from sinais.contas.modelos import ItemPayout, StatusUsuario
from sinais.contas.servico import ErroConta

rotas = APIRouter(prefix="/api/admin", tags=["administração"], responses=RESPOSTAS_ERRO)
LIMITE_LOGS = 500


@rotas.get("/usuarios", response_model=list[e.UsuarioAdmin])
async def listar_usuarios(
    ctx: Admin,
    s: Svc,
    busca: Annotated[str | None, Query(max_length=120)] = None,
    status: Literal["ativo", "bloqueado", "desativado"] | None = None,
) -> list[e.UsuarioAdmin]:
    fichas = await s.admin.listar_usuarios(busca or None, StatusUsuario(status) if status else None)
    return [usuario_admin(f, ctx.agora) for f in fichas]


@rotas.post("/usuarios", response_model=e.UsuarioAdmin, status_code=201)
async def criar_usuario(corpo: e.NovoUsuarioEntrada, ctx: AdminMutacao, s: Svc) -> e.UsuarioAdmin:
    f = await s.admin.criar_usuario(
        ctx, corpo.email, corpo.nome, corpo.senha_temporaria, corpo.plano, corpo.vence_em
    )
    return usuario_admin(f, ctx.agora)


@rotas.patch("/usuarios/{usuario_id}", response_model=e.UsuarioAdmin)
async def editar_usuario(
    usuario_id: int, corpo: e.EdicaoUsuarioEntrada, ctx: AdminMutacao, s: Svc
) -> e.UsuarioAdmin:
    f = await s.admin.editar_usuario(
        ctx,
        usuario_id,
        nome=corpo.nome,
        email=corpo.email,
        status=StatusUsuario(corpo.status) if corpo.status else None,
        senha_temporaria=corpo.senha_temporaria,
    )
    return usuario_admin(f, ctx.agora)


@rotas.get("/planos", response_model=list[e.Plano])
async def listar_planos(ctx: Admin, s: Svc) -> list[e.Plano]:
    return [plano_saida(p) for p in await s.admin.listar_planos()]


@rotas.post("/planos", response_model=e.Plano, status_code=201)
async def criar_plano(corpo: e.PlanoEntrada, ctx: AdminMutacao, s: Svc) -> e.Plano:
    p = await s.admin.criar_plano(
        ctx,
        corpo.nome,
        corpo.duracao_dias,
        corpo.preco_centavos,
        recursos_de(corpo.recursos),
        corpo.ativo,
    )
    return plano_saida(p)


@rotas.patch("/planos", response_model=e.Plano)
async def editar_plano_pelo_corpo(corpo: e.PlanoEdicao, ctx: AdminMutacao, s: Svc) -> e.Plano:
    """Mesma edição de ``PATCH /planos/{id}``, com o ``id`` no corpo (plano inteiro)."""
    if corpo.id is None:
        raise ErroConta(422, "validacao", "Dados inválidos em: id.")
    return await _editar_plano(corpo.id, corpo, ctx, s)


@rotas.patch("/planos/{plano_id}", response_model=e.Plano)
async def editar_plano(plano_id: int, corpo: e.PlanoEdicao, ctx: AdminMutacao, s: Svc) -> e.Plano:
    return await _editar_plano(plano_id, corpo, ctx, s)


async def _editar_plano(plano_id: int, corpo: e.PlanoEdicao, ctx: Contexto, s: Servicos) -> e.Plano:
    if corpo.id is not None and corpo.id != plano_id:
        raise ErroConta(422, "validacao", "O id do corpo difere do id da rota.")
    p = await s.admin.editar_plano(
        ctx,
        plano_id,
        nome=corpo.nome,
        duracao_dias=corpo.duracao_dias,
        preco_centavos=corpo.preco_centavos,
        recursos=recursos_de(corpo.recursos) if corpo.recursos else None,
        ativo=corpo.ativo,
    )
    return plano_saida(p)


@rotas.post("/assinaturas", response_model=e.Assinatura, status_code=201)
async def criar_assinatura(corpo: e.AssinaturaEntrada, ctx: AdminMutacao, s: Svc) -> e.Assinatura:
    a = await s.admin.criar_assinatura(
        ctx, corpo.usuario_id, corpo.plano_id, corpo.inicio, corpo.fim
    )
    return assinatura_saida(a)


async def _emails(s: Servicos, ids: set[int | None]) -> dict[int, str]:
    emails: dict[int, str] = {}
    for uid in ids:
        if uid is not None:
            u = await s.contas.repo.usuario_por_id(uid)
            if u is not None:
                emails[uid] = u.email
    return emails


@rotas.get("/acessos", response_model=list[e.Acesso])
async def acessos(ctx: Admin, s: Svc, usuario_id: int | None = None) -> list[e.Acesso]:
    registros = await s.admin.acessos(usuario_id, LIMITE_LOGS)
    emails = await _emails(s, {r.usuario_id for r in registros})
    return [
        acesso_saida(r, emails.get(r.usuario_id) if r.usuario_id is not None else None)
        for r in registros
    ]


@rotas.get("/auditoria", response_model=list[e.RegistroAuditoria])
async def auditoria(ctx: Admin, s: Svc) -> list[e.RegistroAuditoria]:
    registros = await s.admin.auditoria(LIMITE_LOGS)
    emails = await _emails(s, {r.admin_id for r in registros})
    return [auditoria_saida(r, emails.get(r.admin_id)) for r in registros]


@rotas.get("/corretoras/exnova/payout", response_model=list[e.Payout])
async def payout(ctx: Admin, s: Svc) -> list[e.Payout]:
    return [payout_saida(i) for i in await s.admin.payouts()]


@rotas.put("/corretoras/exnova/payout", response_model=list[e.Payout])
async def substituir_payout(corpo: list[e.Payout], ctx: AdminMutacao, s: Svc) -> list[e.Payout]:
    itens = [ItemPayout(p.simbolo, p.expiracao, p.payout) for p in corpo]
    return [payout_saida(i) for i in await s.admin.substituir_payouts(ctx, itens)]


@rotas.get("/qualidade", response_model=list[e.EventoQualidade])
async def qualidade(ctx: Admin, s: Svc) -> list[e.EventoQualidade]:
    return [qualidade_saida(q) for q in await s.mercado.qualidade_recentes(LIMITE_LOGS)]
