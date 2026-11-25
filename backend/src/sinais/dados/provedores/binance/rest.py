"""Cliente REST da Binance Spot para histórico de candles e hora do servidor."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from sinais.core.tempo import InstanteMs
from sinais.dados.modelos import Candle, IntervaloColeta
from sinais.dados.provedores.backoff import atraso_backoff
from sinais.dados.provedores.binance.parsing import ErroParsing, de_linha_rest
from sinais.logs import obter_logger

_log = obter_logger(__name__)


class ErroLimiteTaxa(Exception):
    """A Binance bloqueou o IP (HTTP 418). Esperar ``espera_s`` antes de qualquer chamada."""

    def __init__(self, espera_s: float) -> None:
        super().__init__(f"limite de requisições da Binance: aguardar {espera_s:.0f} s")
        self.espera_s = espera_s


def _retry_after(resposta: httpx.Response, padrao: float) -> float:
    try:
        return float(resposta.headers.get("Retry-After", padrao))
    except ValueError:
        return padrao


class ClienteRestBinance:
    def __init__(
        self,
        base_url: str,
        http: httpx.AsyncClient,
        dormir: Callable[[float], Awaitable[None]] = asyncio.sleep,
        tentativas: int = 5,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._http = http
        self._dormir = dormir
        self._tentativas = tentativas

    async def _get(self, caminho: str, params: dict[str, str] | None = None) -> Any:
        for tentativa in range(self._tentativas):
            ultima = tentativa == self._tentativas - 1
            try:
                r = await self._http.get(self._base + caminho, params=params, timeout=10.0)
            except httpx.TransportError as erro:
                if ultima:
                    raise
                espera = atraso_backoff(tentativa)
                _log.warning(
                    "binance.rest.falha_rede",
                    extra={"campos": {"caminho": caminho, "erro": str(erro), "espera_s": espera}},
                )
                await self._dormir(espera)
                continue
            if r.status_code == 418:
                raise ErroLimiteTaxa(_retry_after(r, 300.0))
            if r.status_code == 429 or r.status_code >= 500:
                if ultima:
                    r.raise_for_status()
                espera = (
                    _retry_after(r, 60.0) if r.status_code == 429 else atraso_backoff(tentativa)
                )
                _log.warning(
                    "binance.rest.nova_tentativa",
                    extra={
                        "campos": {"caminho": caminho, "status": r.status_code, "espera_s": espera}
                    },
                )
                await self._dormir(espera)
                continue
            r.raise_for_status()
            return r.json()
        raise RuntimeError("inalcançável")  # pragma: no cover

    async def hora_servidor(self) -> InstanteMs:
        dados = await self._get("/api/v3/time")
        return int(dados["serverTime"])

    async def klines(
        self,
        simbolo: str,
        intervalo: IntervaloColeta,
        inicio: InstanteMs,
        fim: InstanteMs,
        limite: int = 1000,
    ) -> list[Candle]:
        """Candles com abertura em ``[inicio, fim)``. Uma linha malformada falha a página."""
        params = {
            "symbol": simbolo,
            "interval": intervalo.value,
            "startTime": str(inicio),
            "endTime": str(fim - 1),
            "limit": str(limite),
        }
        dados = await self._get("/api/v3/klines", params)
        if not isinstance(dados, list):
            raise ErroParsing(f"{simbolo} {intervalo.value}: resposta de klines não é lista")
        return [de_linha_rest(simbolo, intervalo, linha) for linha in dados]
