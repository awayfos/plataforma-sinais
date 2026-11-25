"""``/api/auth``: login e logout por cookie de sessão."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from sinais.api import esquemas as e
from sinais.api.dependencias import CABECALHO_CSRF, COOKIE_CSRF, COOKIE_SESSAO, Svc, ip_cliente
from sinais.api.erros import RESPOSTAS_ERRO
from sinais.api.servicos import Servicos
from sinais.api.visoes import usuario_saida
from sinais.contas.servico import ErroConta

rotas = APIRouter(prefix="/api/auth", tags=["autenticação"], responses=RESPOSTAS_ERRO)


def _cookies(resposta: Response, s: Servicos, token: str, csrf: str) -> None:
    validade = s.contas.params.sessao_duracao_ms // 1000
    resposta.set_cookie(
        COOKIE_SESSAO,
        token,
        max_age=validade,
        httponly=True,
        secure=s.cookie_seguro,
        samesite="lax",
        path="/",
    )
    resposta.set_cookie(
        COOKIE_CSRF,
        csrf,
        max_age=validade,
        httponly=False,
        secure=s.cookie_seguro,
        samesite="lax",
        path="/",
    )


def _apagar_cookies(resposta: Response, s: Servicos) -> None:
    for nome, http_only in ((COOKIE_SESSAO, True), (COOKIE_CSRF, False)):
        resposta.delete_cookie(
            nome, path="/", secure=s.cookie_seguro, httponly=http_only, samesite="lax"
        )


@rotas.post("/login", response_model=e.RespostaLogin, responses={423: {"model": e.RespostaErro}})
async def login(
    corpo: e.LoginEntrada, request: Request, response: Response, s: Svc
) -> e.RespostaLogin:
    r = await s.contas.login(
        corpo.email,
        corpo.senha,
        corpo.totp,
        ip_cliente(request, s),
        request.headers.get("user-agent", "")[:256],
    )
    _cookies(response, s, r.token, r.csrf)
    ctx = await s.contas.autenticar(r.token)
    return e.RespostaLogin(usuario=usuario_saida(ctx.usuario, ctx.assinatura, ctx.plano, ctx.agora))


@rotas.post("/logout", status_code=204)
async def logout(request: Request, s: Svc) -> Response:
    token = request.cookies.get(COOKIE_SESSAO)
    try:
        ctx = await s.contas.autenticar(token)
    except ErroConta:
        ctx = None
    if ctx is not None:
        s.contas.verificar_csrf(
            ctx, request.headers.get(CABECALHO_CSRF), request.cookies.get(COOKIE_CSRF)
        )
        await s.contas.logout(
            token, ip_cliente(request, s), request.headers.get("user-agent", "")[:256]
        )
    resposta = Response(status_code=204)
    _apagar_cookies(resposta, s)
    return resposta
