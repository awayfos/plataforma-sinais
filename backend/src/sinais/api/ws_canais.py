"""Canais do WebSocket: mensagens do cliente, distribuição (fan-out) e tradução de eventos.

Uma única leitura do Redis Streams por processo da API alimenta todos os assinantes.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Literal
from urllib.parse import urlsplit

from sinais.api.esquemas import decimal_texto
from sinais.api.sinais_ao_vivo import EXPIRACOES, BuscaCampeao, sinais_para
from sinais.core.dominio import TempoGrafico
from sinais.eventos.contratos import STREAM_ANALISE_ATUALIZADA, STREAM_CANDLE_FECHADO

type TipoCanal = Literal["candles", "analise", "sinais"]
TAMANHO_MAXIMO = 512
_POR_DURACAO = {tg.duracao_ms: tg.value for tg in TempoGrafico}


class ErroMensagem(ValueError):
    """Mensagem do cliente fora do formato."""


@dataclass(frozen=True, slots=True)
class Canal:
    tipo: TipoCanal
    simbolo: str
    tg: str | None

    @property
    def nome(self) -> str:
        base = f"{self.tipo}:{self.simbolo}"
        return f"{base}:{self.tg}" if self.tg else base


def interpretar(
    texto: str, simbolos: Sequence[str]
) -> tuple[Literal["assinar", "cancelar"], Canal]:
    if len(texto) > TAMANHO_MAXIMO:
        raise ErroMensagem("mensagem grande demais")
    try:
        msg = json.loads(texto)
    except ValueError:
        raise ErroMensagem("JSON inválido") from None
    if not isinstance(msg, dict):
        raise ErroMensagem("esperado um objeto")
    acao, nome = msg.get("acao"), msg.get("canal")
    if acao not in ("assinar", "cancelar") or not isinstance(nome, str):
        raise ErroMensagem("use {acao: assinar|cancelar, canal}")
    partes = nome.split(":")
    tipo = partes[0]
    if len(partes) < 2 or partes[1] not in simbolos:
        raise ErroMensagem("canal ou ativo desconhecido")
    if tipo == "candles" and len(partes) == 3 and partes[2] in _POR_DURACAO.values():
        return acao, Canal("candles", partes[1], partes[2])
    if tipo in ("analise", "sinais") and len(partes) == 2:
        return acao, Canal(tipo, partes[1], None)  # type: ignore[arg-type]
    raise ErroMensagem("canal desconhecido")


def origem_permitida(origem: str | None, host: str | None, permitidas: Sequence[str]) -> bool:
    """Defesa contra sequestro de WebSocket entre sites: a sessão vai no cookie, então só se
    aceita a própria origem (mesmo host) ou uma da lista. Sem ``Origin`` (cliente que não é
    navegador) é aceito: o cookie continua sendo exigido."""
    if origem is None:
        return True
    if origem in permitidas:
        return True
    return bool(host) and urlsplit(origem).netloc == host


@dataclass(eq=False)
class Assinante:
    fila: asyncio.Queue[dict[str, Any]]
    canais: set[str] = field(default_factory=set)


class Distribuidor:
    def __init__(self, tamanho_fila: int = 256) -> None:
        self._tamanho = tamanho_fila
        self._por_canal: dict[str, set[Assinante]] = {}

    def novo_assinante(self) -> Assinante:
        return Assinante(asyncio.Queue(self._tamanho))

    def assinar(self, a: Assinante, canal: str) -> None:
        a.canais.add(canal)
        self._por_canal.setdefault(canal, set()).add(a)

    def cancelar(self, a: Assinante, canal: str) -> None:
        a.canais.discard(canal)
        grupo = self._por_canal.get(canal)
        if grupo is not None:
            grupo.discard(a)
            if not grupo:
                del self._por_canal[canal]

    def remover(self, a: Assinante) -> None:
        for canal in list(a.canais):
            self.cancelar(a, canal)

    @staticmethod
    def entregar(a: Assinante, mensagem: dict[str, Any]) -> None:
        """Cliente lento perde a mensagem mais antiga, nunca trava os outros."""
        if a.fila.full():
            a.fila.get_nowait()
        a.fila.put_nowait(mensagem)

    def publicar(self, canal: str, dados: Any) -> int:
        grupo = self._por_canal.get(canal, set())
        for a in grupo:
            self.entregar(a, {"canal": canal, "dados": dados})
        return len(grupo)


def _texto_decimal(valor: str) -> str:
    return decimal_texto(Decimal(valor))


def traduzir_evento(
    stream: str, campos: Mapping[str, str], campeao: BuscaCampeao | None = None
) -> list[tuple[str, Any]]:
    """Evento do Redis Streams → [(canal, dados)] no formato do contrato."""
    try:
        if stream == STREAM_CANDLE_FECHADO:
            tg = _POR_DURACAO.get(int(campos["intervalo_ms"]))
            if tg is None:
                return []
            dados: dict[str, Any] = {"t": int(campos["abertura"])}
            dados.update({k: _texto_decimal(campos[k]) for k in ("o", "h", "l", "c", "v")})
            return [(f"candles:{campos['simbolo']}:{tg}", {**dados, "fechado": True})]
        if stream == STREAM_ANALISE_ATUALIZADA:
            simbolo = campos["simbolo"]
            busca = campeao or (lambda s, e: None)
            sinais = [s.model_dump() for s in sinais_para(simbolo, EXPIRACOES, busca)]
            return [
                (f"analise:{simbolo}", json.loads(campos["analise"])),
                (f"sinais:{simbolo}", sinais),
            ]
    except (KeyError, ValueError, InvalidOperation):
        return []
    return []
