"""``/api/ws``: WebSocket multiplexado por canal, com a mesma sessão por cookie.

Sessão e assinatura são checadas na conexão, em cada ``assinar`` e periodicamente
(``ws_verificacao_s``); antes de cada envio o vencimento já conhecido é conferido sem ir ao
banco. Fecha com 4401 (sessão revogada/expirada) ou 4402 (assinatura vencida).
"""

from __future__ import annotations

import asyncio
import json
from contextlib import suppress
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from sinais.api.dependencias import COOKIE_SESSAO
from sinais.api.servicos import Servicos
from sinais.api.sinais_ao_vivo import EXPIRACOES, sinais_para
from sinais.api.ws_canais import Distribuidor, ErroMensagem, interpretar, origem_permitida
from sinais.contas.autorizacao import expiracoes_permitidas, pode_ver_ativo
from sinais.contas.contexto import Contexto
from sinais.contas.servico import ErroConta
from sinais.logs import obter_logger

_log = obter_logger(__name__)
FECHA_SESSAO = 4401
FECHA_ASSINATURA = 4402
FECHA_ORIGEM = 4403
MAX_CANAIS = 20


class _Fechar(Exception):
    def __init__(self, codigo: int) -> None:
        super().__init__(codigo)
        self.codigo = codigo


class ConexaoWs:
    def __init__(self, websocket: WebSocket, s: Servicos) -> None:
        self._ws = websocket
        self._s = s
        self._token = websocket.cookies.get(COOKIE_SESSAO)
        self._assinante = s.distribuidor.novo_assinante()
        self._ctx: Contexto | None = None

    async def _validar(self) -> Contexto:
        try:
            ctx = await self._s.contas.autenticar(self._token)
        except ErroConta:
            raise _Fechar(FECHA_SESSAO) from None
        try:
            self._s.contas.exigir_assinatura(ctx)
        except ErroConta:
            raise _Fechar(FECHA_ASSINATURA) from None
        self._ctx = ctx
        return ctx

    def _vencida(self) -> bool:
        ctx = self._ctx
        if ctx is None or ctx.admin or ctx.assinatura is None:
            return False
        return self._s.contas.relogio.agora_ms() >= ctx.assinatura.fim

    def _enfileirar(self, mensagem: dict[str, Any]) -> None:
        Distribuidor.entregar(self._assinante, mensagem)

    async def _assinar(self, nome: str, simbolo: str, tipo: str) -> None:
        ctx = await self._validar()
        if not pode_ver_ativo(ctx, simbolo):
            self._enfileirar(
                {
                    "canal": nome,
                    "erro": {
                        "codigo": "ativo_nao_incluido",
                        "mensagem": "Este ativo não está incluído no seu plano.",
                    },
                }
            )
            return
        if nome not in self._assinante.canais and len(self._assinante.canais) >= MAX_CANAIS:
            self._enfileirar(
                {
                    "canal": nome,
                    "erro": {"codigo": "limite_canais", "mensagem": "Canais demais nesta conexão."},
                }
            )
            return
        self._s.distribuidor.assinar(self._assinante, nome)
        if tipo == "analise":
            texto = await self._s.analises.obter(simbolo)
            if texto is not None:
                self._enfileirar({"canal": nome, "dados": json.loads(texto)})
        elif tipo == "sinais":
            lista = sinais_para(simbolo, EXPIRACOES, self._s.campeao)
            self._enfileirar({"canal": nome, "dados": [x.model_dump() for x in lista]})

    async def _receber(self) -> None:
        while True:
            msg = await self._ws.receive()
            if msg["type"] == "websocket.disconnect":
                raise WebSocketDisconnect(msg.get("code", 1000))
            texto = msg.get("text")
            if texto is None:
                dados = msg.get("bytes") or b""
                texto = dados.decode("utf-8", errors="replace")
            try:
                acao, canal = interpretar(texto, self._s.simbolos)
            except ErroMensagem as erro:
                self._enfileirar({"erro": {"codigo": "mensagem_invalida", "mensagem": str(erro)}})
                continue
            if acao == "assinar":
                await self._assinar(canal.nome, canal.simbolo, canal.tipo)
            else:
                self._s.distribuidor.cancelar(self._assinante, canal.nome)

    async def _enviar(self) -> None:
        while True:
            msg = await self._assinante.fila.get()
            if self._vencida():
                raise _Fechar(FECHA_ASSINATURA)
            canal = msg.get("canal", "")
            if canal.startswith("sinais:") and isinstance(msg.get("dados"), list) and self._ctx:
                permitidas = set(expiracoes_permitidas(self._ctx, EXPIRACOES))
                msg = {
                    **msg,
                    "dados": [x for x in msg["dados"] if x.get("expiracao") in permitidas],
                }
            await self._ws.send_json(msg)

    async def _verificar(self) -> None:
        while True:
            await asyncio.sleep(self._s.ws_verificacao_s)
            await self._validar()
            if self._vencida():
                raise _Fechar(FECHA_ASSINATURA)

    async def executar(self) -> None:
        codigo: int | None = 1000
        try:
            await self._validar()
            tarefas = [
                asyncio.create_task(self._receber()),
                asyncio.create_task(self._enviar()),
                asyncio.create_task(self._verificar()),
            ]
            feitas, pendentes = await asyncio.wait(tarefas, return_when=asyncio.FIRST_COMPLETED)
            for t in pendentes:
                t.cancel()
            await asyncio.gather(*pendentes, return_exceptions=True)
            for t in feitas:
                erro = t.exception()
                if isinstance(erro, _Fechar):
                    codigo = erro.codigo
                elif isinstance(erro, WebSocketDisconnect):
                    codigo = None
                elif erro is not None:
                    _log.error("ws.erro", extra={"campos": {"erro": type(erro).__name__}})
                    codigo = 1011
        except _Fechar as f:
            codigo = f.codigo
        finally:
            self._s.distribuidor.remover(self._assinante)
        if codigo is not None:
            with suppress(Exception):
                await self._ws.close(code=codigo)


async def rota_ws(websocket: WebSocket) -> None:
    s: Servicos = websocket.app.state.servicos
    if not origem_permitida(
        websocket.headers.get("origin"), websocket.headers.get("host"), s.origens_permitidas
    ):
        await websocket.close(code=FECHA_ORIGEM)
        return
    await websocket.accept()
    await ConexaoWs(websocket, s).executar()
