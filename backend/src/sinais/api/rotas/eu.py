"""``/api/eu``: a própria conta. Exige sessão, não assinatura (o usuário precisa ver que a
assinatura venceu e conseguir trocar a senha)."""

from __future__ import annotations

from fastapi import APIRouter, Response

from sinais.api import esquemas as e
from sinais.api.dependencias import Mutacao, Sessao, Svc
from sinais.api.erros import RESPOSTAS_ERRO
from sinais.api.visoes import usuario_saida
from sinais.contas.modelos import Modo

rotas = APIRouter(prefix="/api/eu", tags=["conta"], responses=RESPOSTAS_ERRO)


@rotas.get("", response_model=e.Usuario)
async def eu(ctx: Sessao) -> e.Usuario:
    return usuario_saida(ctx.usuario, ctx.assinatura, ctx.plano, ctx.agora)


@rotas.post("/senha", status_code=204)
async def trocar_senha(corpo: e.SenhaEntrada, ctx: Mutacao, s: Svc) -> Response:
    await s.contas.trocar_senha(ctx, corpo.senha_atual, corpo.senha_nova)
    return Response(status_code=204)


@rotas.patch("/preferencias", response_model=e.Usuario)
async def preferencias(corpo: e.PreferenciasEntrada, ctx: Mutacao, s: Svc) -> e.Usuario:
    modo = Modo(corpo.modo) if corpo.modo else None
    u = await s.contas.preferencias(ctx, modo, corpo.layout)
    return usuario_saida(u, ctx.assinatura, ctx.plano, ctx.agora)
