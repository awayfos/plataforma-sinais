"""Velas em formação na API, tick a tick, para o gráfico ao vivo.

Ticks chegam do Redis Pub/Sub ``ticks:{SIMBOLO}``; os 1m oficiais, do stream ``candle.fechado``.
A cada ``INTERVALO_S`` (100 ms) o gestor publica, só nos canais com assinantes e só para os
símbolos que mudaram, o valor mais recente (coalescido: o último vence):

- ``candles:SIMBOLO:TG`` → ``{t, o, h, l, c, v, fechado: false}``
- ``preco:SIMBOLO`` → ``{preco, t}``

O ``fechado: true`` continua saindo do ``candle.fechado`` (oficial). Ao assinar, o cliente
recebe na hora a vela em formação (``snapshot``).
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any

from sinais.api.ws_canais import Distribuidor
from sinais.core.dominio import TempoGrafico, abertura_candle
from sinais.core.tempo import Relogio
from sinais.dados.modelos import Candle, IntervaloColeta, decimal_texto
from sinais.dados.vela_formacao import Negocio, Vela, VelaEmFormacao
from sinais.logs import obter_logger
from sinais.persistencia.repositorio import RepositorioCandles

_log = obter_logger(__name__)
INTERVALO_S = 0.1
_M = 60_000
_POR_ROTULO = {tg.value: tg for tg in TempoGrafico}


def _dados_vela(v: Vela) -> dict[str, Any]:
    return {
        "t": v.t,
        "o": decimal_texto(v.o),
        "h": decimal_texto(v.h),
        "l": decimal_texto(v.l),
        "c": decimal_texto(v.c),
        "v": decimal_texto(v.v),
        "fechado": False,
    }


def candle_do_evento(campos: Mapping[str, str]) -> Candle:
    """1m oficial a partir do evento ``candle.fechado`` (campos que a vela usa)."""
    zero = Decimal(0)
    return Candle(
        simbolo=campos["simbolo"],
        intervalo_ms=int(campos["intervalo_ms"]),
        abertura=int(campos["abertura"]),
        abertura_preco=Decimal(campos["o"]),
        maxima=Decimal(campos["h"]),
        minima=Decimal(campos["l"]),
        fechamento=Decimal(campos["c"]),
        volume=Decimal(campos["v"]),
        volume_cotacao=zero,
        negocios=0,
        volume_compra_agressora=zero,
        fonte=campos.get("fonte", "binance"),
    )


class GestorVelas:
    def __init__(
        self,
        simbolos: Sequence[str],
        repo: RepositorioCandles,
        relogio: Relogio,
        distribuidor: Distribuidor,
    ) -> None:
        self._repo = repo
        self._relogio = relogio
        self._d = distribuidor
        self._velas = {s: VelaEmFormacao(s) for s in simbolos}
        self._mudaram: set[str] = set()

    async def carregar(self, simbolos: Sequence[str] | None = None, ate: int = 0) -> None:
        """1m oficiais do banco desde o início da semana atual (o maior tempo gráfico) até
        agora (ou até ``ate``, o fim do evento que pediu a recarga, se for depois)."""
        agora = max(self._relogio.agora_ms(), ate)
        inicio = abertura_candle(agora, TempoGrafico.W1)
        for s in simbolos or list(self._velas):
            fechados = await self._repo.listar(s, IntervaloColeta.M1, inicio, agora + _M)
            self._velas[s].carregar(fechados)
            _log.info("velas.carregadas", extra={"campos": {"simbolo": s, "n": len(fechados)}})

    def ao_negocio(self, simbolo: str, n: Negocio) -> None:
        v = self._velas.get(simbolo)
        if v is not None and v.adicionar(n):
            self._mudaram.add(simbolo)

    async def ao_fechado(self, campos: Mapping[str, str]) -> None:
        if campos.get("intervalo_ms") != str(_M) or campos.get("simbolo") not in self._velas:
            return
        c = candle_do_evento(campos)
        v = self._velas[c.simbolo]
        if v.fechar_1m(c):
            self._mudaram.add(c.simbolo)
        if v.precisa_recarregar:
            await self.carregar([c.simbolo], ate=c.fechamento_ms)
            if v.fechado_ate is None or v.fechado_ate < c.fechamento_ms:
                # Banco atrás do evento: o oficial recebido completa a soma; se ainda houver
                # lacuna (ou nada no banco), fica pedindo recarga até o banco alcançar.
                v.fechar_1m(c)

    def vela_oficial_ok(self, simbolo: str) -> bool:
        return not self._velas[simbolo].precisa_recarregar

    def snapshot(self, canal: str) -> dict[str, Any] | None:
        partes = canal.split(":")
        v = self._velas.get(partes[1]) if len(partes) > 1 else None
        if v is None:
            return None
        if partes[0] == "candles" and len(partes) == 3 and partes[2] in _POR_ROTULO:
            vela = v.vela(_POR_ROTULO[partes[2]])
            return _dados_vela(vela) if vela else None
        if partes[0] == "preco" and len(partes) == 2:
            ultimo = v.ultimo_preco()
            return {"preco": decimal_texto(ultimo[0]), "t": ultimo[1]} if ultimo else None
        return None

    def drenar(self) -> list[tuple[str, dict[str, Any]]]:
        """Valores atuais dos canais com assinantes dos símbolos que mudaram desde a última vez."""
        saida: list[tuple[str, dict[str, Any]]] = []
        mudaram, self._mudaram = self._mudaram, set()
        for s in sorted(mudaram):
            canais = [f"candles:{s}:{tg.value}" for tg in TempoGrafico] + [f"preco:{s}"]
            for canal in canais:
                if not self._d.tem_assinantes(canal):
                    continue
                dados = self.snapshot(canal)
                if dados is not None:
                    saida.append((canal, dados))
        return saida

    async def executar(self, intervalo_s: float = INTERVALO_S) -> None:
        """Carrega do banco e publica no máximo uma mensagem por canal a cada ``intervalo_s``."""
        await self.carregar()
        while True:
            await asyncio.sleep(intervalo_s)
            for canal, dados in self.drenar():
                self._d.publicar(canal, dados)
