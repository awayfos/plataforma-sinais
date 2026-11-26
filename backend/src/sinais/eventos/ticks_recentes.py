"""Negócios recentes por símbolo no Redis, para ressincronizar a vela em formação da API.

O Pub/Sub ``ticks:{SIMBOLO}`` não guarda nada: uma API que reinicia (ou cujo Pub/Sub reconecta)
no meio do minuto perderia os negócios anteriores e mostraria abertura, máxima, mínima e volume
errados até o 1m oficial chegar. Por isso o processo de ticks também grava cada negócio no
stream ``ticks.recentes:{SIMBOLO}`` (minuto atual e anterior, aparado por ``MINID`` e com
validade de ``VALIDADE_MS``); a API relê esse stream a cada (re)assinatura do Pub/Sub antes de
seguir ao vivo. Repetidos são descartados pelo id do aggTrade na vela.

O negócio é gravado no stream **antes** do ``PUBLISH``: quem assinar entre os dois comandos
ainda o encontra na releitura.
"""

from __future__ import annotations

from typing import Any

from sinais.core.tempo import InstanteMs, Relogio

_M = 60_000
CAMPO = "p"
VALIDADE_MS = 3 * _M


def chave_recentes(simbolo: str) -> str:
    return f"ticks.recentes:{simbolo}"


def inicio_retencao(agora_ms: InstanteMs) -> InstanteMs:
    """Abertura do minuto anterior: o que for mais antigo sai do stream."""
    return agora_ms - agora_ms % _M - _M


class PublicadorTicksRedis:
    """``Publicar(canal, texto)`` do processo de ticks: stream curto + Pub/Sub, num pipeline."""

    def __init__(self, redis: Any, relogio: Relogio) -> None:
        self._redis = redis
        self._relogio = relogio

    async def __call__(self, canal: str, texto: str) -> None:
        simbolo = canal.split(":", 1)[1]
        chave = chave_recentes(simbolo)
        pipe = self._redis.pipeline(transaction=False)
        pipe.xadd(
            chave,
            {CAMPO: texto},
            minid=inicio_retencao(self._relogio.agora_ms()),
            approximate=True,
        )
        pipe.publish(canal, texto)
        pipe.pexpire(chave, VALIDADE_MS)
        await pipe.execute()


async def ler_recentes(redis: Any, simbolo: str) -> list[str]:
    """Payloads guardados de ``simbolo``, do mais antigo ao mais novo."""
    entradas = await redis.xrange(chave_recentes(simbolo))
    return [campos[CAMPO] for _, campos in entradas if CAMPO in campos]
