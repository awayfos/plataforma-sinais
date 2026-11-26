"""Formato único de erro do contrato: ``{"erro": {"codigo", "mensagem"}}``."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from sinais.api.esquemas import RespostaErro
from sinais.contas.servico import ErroConta
from sinais.logs import obter_logger

_log = obter_logger(__name__)

_POR_STATUS = {
    400: ("requisicao_invalida", "Requisição inválida."),
    401: ("sessao_invalida", "Sessão expirada. Entre de novo."),
    403: ("sem_permissao", "Você não tem permissão para esta ação."),
    404: ("nao_encontrado", "Recurso não encontrado."),
    405: ("metodo_nao_permitido", "Método não permitido."),
    429: ("muitas_tentativas", "Muitas requisições. Aguarde e tente de novo."),
}

# Respostas de erro documentadas no OpenAPI.
RESPOSTAS_ERRO: dict[int | str, dict[str, object]] = {
    s: {"model": RespostaErro} for s in (401, 402, 403, 422, 429)
}


def cabecalhos_seguranca(https: bool, documentacao: bool = False) -> dict[str, str]:
    h = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
        "Cache-Control": "no-store",
    }
    if not documentacao:
        h["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    if https:
        h["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return h


def resposta_erro(status: int, codigo: str, mensagem: str) -> JSONResponse:
    return JSONResponse({"erro": {"codigo": codigo, "mensagem": mensagem}}, status_code=status)


def _campos(erro: RequestValidationError) -> str:
    nomes = []
    for e in erro.errors():
        loc = [str(p) for p in e.get("loc", ()) if p not in ("body", "query", "path")]
        if loc:
            nomes.append(".".join(loc))
    return ", ".join(dict.fromkeys(nomes)) or "corpo"


def instalar(app: FastAPI, https: bool = True) -> None:
    @app.exception_handler(ErroConta)
    async def _conta(_: Request, erro: ErroConta) -> JSONResponse:
        return resposta_erro(erro.status, erro.codigo, erro.mensagem)

    @app.exception_handler(RequestValidationError)
    async def _validacao(_: Request, erro: RequestValidationError) -> JSONResponse:
        return resposta_erro(422, "validacao", f"Dados inválidos em: {_campos(erro)}.")

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, erro: StarletteHTTPException) -> JSONResponse:
        if erro.status_code == 400:
            # O FastAPI responde 400 quando não consegue ler o corpo (ex.: JSON aninhado demais
            # para o parser). Para o cliente é dado inválido, como no contrato: 422.
            return resposta_erro(422, "validacao", "Dados inválidos: corpo da requisição ilegível.")
        codigo, mensagem = _POR_STATUS.get(erro.status_code, ("erro", "Erro na requisição."))
        return resposta_erro(erro.status_code, codigo, mensagem)

    @app.exception_handler(RecursionError)
    async def _recursao(_: Request, erro: RecursionError) -> JSONResponse:
        # JSON aninhado demais para o parser: erro do cliente, não do servidor.
        return resposta_erro(422, "validacao", "Dados inválidos: aninhamento demais.")

    @app.exception_handler(Exception)
    async def _interno(request: Request, erro: Exception) -> JSONResponse:
        _log.error(
            "api.erro_interno",
            extra={"campos": {"rota": request.url.path, "erro": type(erro).__name__}},
        )
        # Esta resposta sai pelo ServerErrorMiddleware, por fora do middleware de cabeçalhos.
        r = resposta_erro(500, "erro_interno", "Erro interno. Tente de novo em instantes.")
        r.headers.update(cabecalhos_seguranca(https))
        return r
