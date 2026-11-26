"""Negócios (aggTrade da Binance): leitura do WebSocket e do REST e o formato do Pub/Sub.

Canal Redis Pub/Sub ``ticks:{SIMBOLO}`` (efêmero, não persistido). Payload JSON::

    {"versao": "1", "simbolo": "BTCUSDT", "id": 42, "preco": "58398.01", "qtd": "0.0012",
     "t": 1795597200123, "maker": true}

``id`` é o id do aggTrade, ``t`` o horário do negócio (ms UTC), ``maker`` = comprador é maker.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Any

from sinais.dados.modelos import decimal_texto
from sinais.dados.vela_formacao import Negocio

VERSAO = "1"


class ErroNegocio(ValueError):
    """Mensagem de negócio fora do formato."""


def canal_ticks(simbolo: str) -> str:
    return f"ticks:{simbolo}"


def _negocio(d: Mapping[str, Any], id_: str, preco: str, qtd: str, t: str, maker: str) -> Negocio:
    try:
        n = Negocio(
            id=int(d[id_]),
            preco=Decimal(str(d[preco])),
            qtd=Decimal(str(d[qtd])),
            t=int(d[t]),
            comprador_maker=bool(d[maker]),
        )
    except (KeyError, TypeError, ValueError, InvalidOperation) as erro:
        raise ErroNegocio(f"negócio inválido: {erro!r}") from None
    if n.t < 0 or not n.preco.is_finite() or n.preco <= 0 or not n.qtd.is_finite() or n.qtd < 0:
        raise ErroNegocio("negócio com valores fora da faixa")
    return n


def de_agg_trade_ws(texto: str) -> tuple[str, Negocio] | None:
    """Mensagem do stream combinado ``<simbolo>@aggTrade``; outros eventos → None."""
    try:
        msg = json.loads(texto)
    except ValueError:
        raise ErroNegocio("JSON inválido") from None
    dados = msg.get("data", msg) if isinstance(msg, dict) else None
    if not isinstance(dados, dict):
        raise ErroNegocio("mensagem sem objeto de dados")
    if dados.get("e") != "aggTrade":
        return None
    simbolo = dados.get("s")
    if not isinstance(simbolo, str) or not simbolo:
        raise ErroNegocio("aggTrade sem símbolo")
    return simbolo, _negocio(dados, "a", "p", "q", "T", "m")


def de_agg_trade_rest(item: Mapping[str, Any]) -> Negocio:
    """Item de ``GET /api/v3/aggTrades``."""
    return _negocio(item, "a", "p", "q", "T", "m")


def para_payload(simbolo: str, n: Negocio) -> str:
    return json.dumps(
        {
            "versao": VERSAO,
            "simbolo": simbolo,
            "id": n.id,
            "preco": decimal_texto(n.preco),
            "qtd": decimal_texto(n.qtd),
            "t": n.t,
            "maker": n.comprador_maker,
        },
        separators=(",", ":"),
    )


def de_payload(texto: str) -> tuple[str, Negocio]:
    try:
        d = json.loads(texto)
        simbolo = d["simbolo"]
    except (ValueError, KeyError, TypeError):
        raise ErroNegocio("payload inválido") from None
    if not isinstance(simbolo, str):
        raise ErroNegocio("payload sem símbolo")
    return simbolo, _negocio(d, "id", "preco", "qtd", "t", "maker")
