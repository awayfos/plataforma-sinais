"""Conversão das respostas da Binance (REST e WebSocket) em ``Candle``."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from sinais.core.tempo import InstanteMs
from sinais.dados.modelos import Candle, IntervaloColeta

FONTE = "binance"
_INTERVALOS_MS = {i.value: i.duracao_ms for i in IntervaloColeta}


class ErroParsing(ValueError):
    """Resposta da Binance fora do formato esperado."""


@dataclass(frozen=True, slots=True)
class EventoKline:
    candle: Candle
    fechado: bool
    evento_ms: InstanteMs


def _dec(valor: object, campo: str, contexto: str) -> Decimal:
    if not isinstance(valor, str):
        raise ErroParsing(f"{contexto}: campo {campo} deveria ser texto numérico")
    try:
        d = Decimal(valor)
    except InvalidOperation:
        raise ErroParsing(f"{contexto}: campo {campo} não numérico") from None
    if not d.is_finite():
        raise ErroParsing(f"{contexto}: campo {campo} não finito")
    return d


def _int(valor: object, campo: str, contexto: str) -> int:
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ErroParsing(f"{contexto}: campo {campo} deveria ser inteiro")
    return valor


def _montar(contexto: str, **campos: Any) -> Candle:
    try:
        return Candle(**campos)
    except ValueError as erro:
        raise ErroParsing(f"{contexto}: {erro}") from None


def de_linha_rest(simbolo: str, intervalo: IntervaloColeta, linha: Sequence[object]) -> Candle:
    """Uma linha de ``GET /api/v3/klines`` (12 campos)."""
    contexto = f"{simbolo} {intervalo.value}"
    if len(linha) < 11:
        raise ErroParsing(f"{contexto}: linha com {len(linha)} campos, esperado 12")
    abertura = _int(linha[0], "open time", contexto)
    contexto = f"{contexto} abertura={abertura}"
    return _montar(
        contexto,
        simbolo=simbolo,
        intervalo_ms=intervalo.duracao_ms,
        abertura=abertura,
        abertura_preco=_dec(linha[1], "open", contexto),
        maxima=_dec(linha[2], "high", contexto),
        minima=_dec(linha[3], "low", contexto),
        fechamento=_dec(linha[4], "close", contexto),
        volume=_dec(linha[5], "volume", contexto),
        volume_cotacao=_dec(linha[7], "quote volume", contexto),
        negocios=_int(linha[8], "trades", contexto),
        volume_compra_agressora=_dec(linha[9], "taker buy base", contexto),
        fonte=FONTE,
    )


def de_mensagem_ws(texto: str) -> EventoKline | None:
    """Mensagem do WebSocket (envelope combinado ou evento cru). ``None`` se não for kline."""
    try:
        obj = json.loads(texto)
    except json.JSONDecodeError:
        raise ErroParsing("mensagem do WebSocket não é JSON válido") from None
    if isinstance(obj, Mapping) and "data" in obj and "stream" in obj:
        obj = obj["data"]
    if not isinstance(obj, Mapping) or obj.get("e") != "kline":
        return None
    k = obj.get("k")
    simbolo = str(obj.get("s", "?"))
    if not isinstance(k, Mapping):
        raise ErroParsing(f"{simbolo}: evento kline sem objeto k")
    intervalo = k.get("i")
    if intervalo not in _INTERVALOS_MS:
        raise ErroParsing(f"{simbolo}: intervalo não coletado: {intervalo!r}")
    abertura = _int(k.get("t"), "t", simbolo)
    contexto = f"{simbolo} {intervalo} abertura={abertura}"
    candle = _montar(
        contexto,
        simbolo=simbolo,
        intervalo_ms=_INTERVALOS_MS[str(intervalo)],
        abertura=abertura,
        abertura_preco=_dec(k.get("o"), "o", contexto),
        maxima=_dec(k.get("h"), "h", contexto),
        minima=_dec(k.get("l"), "l", contexto),
        fechamento=_dec(k.get("c"), "c", contexto),
        volume=_dec(k.get("v"), "v", contexto),
        volume_cotacao=_dec(k.get("q"), "q", contexto),
        negocios=_int(k.get("n"), "n", contexto),
        volume_compra_agressora=_dec(k.get("V"), "V", contexto),
        fonte=FONTE,
    )
    fechado = k.get("x")
    if not isinstance(fechado, bool):
        raise ErroParsing(f"{contexto}: campo x deveria ser booleano")
    return EventoKline(candle, fechado, _int(obj.get("E"), "E", contexto))
