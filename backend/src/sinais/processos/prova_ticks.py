"""Prova de que a vela em formação é igual à da Binance (roda no CI, com rede).

Grava os aggTrades de BTCUSDT e ETHUSDT por pelo menos 3 minutos inteiros (até o fim de um
período de 5m), monta as velas só com os negócios (antes de qualquer reconciliação com o 1m
oficial) e compara O, H, L, C e V de cada minuto, com igualdade exata de ``Decimal``, contra
``GET /api/v3/klines`` 1m, e o 5m que contém o último minuto contra o kline 5m.

Uso: ``python -m sinais.processos.prova_ticks --saida relatorio-ticks.md``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from sinais.core.dominio import TempoGrafico, abertura_candle
from sinais.dados.modelos import Candle
from sinais.dados.negocios import ErroNegocio, de_agg_trade_ws
from sinais.dados.vela_formacao import Negocio, Vela, VelaEmFormacao

_M = 60_000
_5M = 5 * _M
MINIMO_MINUTOS = 3


@dataclass(frozen=True, slots=True)
class Kline:
    t: int
    o: Decimal
    h: Decimal
    l: Decimal  # noqa: E741
    c: Decimal
    v: Decimal


@dataclass(frozen=True, slots=True)
class Linha:
    simbolo: str
    tg: str
    t: int
    nosso: tuple[Decimal, ...] | None
    binance: tuple[Decimal, ...]

    @property
    def igual(self) -> bool:
        return self.nosso == self.binance


def janela_de_gravacao(agora: int, minimo: int = MINIMO_MINUTOS) -> tuple[int, int]:
    """[início, fim): do próximo minuto cheio até o fim do 5m, com ``minimo`` minutos."""
    inicio = agora - agora % _M + _M
    fim = abertura_candle(inicio, TempoGrafico.M5) + _5M
    while (fim - inicio) // _M < minimo:
        fim += _5M
    return inicio, fim


def lacunas_de_id(negocios: Sequence[Negocio]) -> list[tuple[int, int]]:
    ids = sorted({n.id for n in negocios})
    return [(a + 1, b - 1) for a, b in zip(ids, ids[1:], strict=False) if b > a + 1]


def _tupla(v: Vela | Kline) -> tuple[Decimal, ...]:
    return (v.o, v.h, v.l, v.c, v.v)


def comparar(
    simbolo: str,
    negocios: Sequence[Negocio],
    oficiais_antes: Sequence[Candle],
    klines_1m: Sequence[Kline],
    kline_5m: Kline,
) -> tuple[list[Linha], bool]:
    b = VelaEmFormacao(simbolo, (TempoGrafico.M1, TempoGrafico.M5))
    b.carregar(list(oficiais_antes))
    for n in negocios:
        b.adicionar(n)
    linhas = []
    for k in klines_1m:
        m = b.minuto(k.t)
        linhas.append(Linha(simbolo, "1m", k.t, _tupla(m) if m else None, _tupla(k)))
    v5 = b.vela(TempoGrafico.M5)
    nosso5 = _tupla(v5) if v5 is not None and v5.t == kline_5m.t else None
    linhas.append(Linha(simbolo, "5m", kline_5m.t, nosso5, _tupla(kline_5m)))
    return linhas, all(linha.igual for linha in linhas)


def _kline(linha: Sequence[object]) -> Kline:
    t, o, h, lo, c, v = linha[:6]
    return Kline(int(str(t)), *(Decimal(str(x)) for x in (o, h, lo, c, v)))


async def principal(argv: list[str] | None = None) -> int:  # pragma: no cover - rede
    import httpx
    import websockets

    from sinais.core.dominio import ATIVOS_V1
    from sinais.dados.modelos import IntervaloColeta
    from sinais.dados.provedores.binance.rest import ClienteRestBinance
    from sinais.processos.ticks_binance import nomes_streams_negocios

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ws", default="wss://data-stream.binance.vision")
    p.add_argument("--rest", default="https://data-api.binance.vision")
    p.add_argument("--saida", default="relatorio-ticks.md")
    args = p.parse_args(argv)
    simbolos = [a.simbolo for a in ATIVOS_V1]
    inicio, fim = janela_de_gravacao(int(time.time() * 1000))
    gravados: dict[str, list[Negocio]] = {s: [] for s in simbolos}
    url = f"{args.ws}/stream?streams={'/'.join(nomes_streams_negocios(simbolos))}"
    print(f"gravando {(fim - inicio) // _M} minutos: {inicio} → {fim}", flush=True)
    async with websockets.connect(url, ping_interval=None, max_size=2**20) as ws:
        async for texto in ws:
            try:
                lido = de_agg_trade_ws(texto if isinstance(texto, str) else texto.decode())
            except ErroNegocio:
                continue
            if lido is None:
                continue
            s, n = lido
            if inicio <= n.t < fim:
                gravados[s].append(n)
            if time.time() * 1000 > fim + 3000:
                break
    ok_geral = True
    saida = [
        "| ativo | tg | abertura (ms) | nosso O/H/L/C/V | Binance O/H/L/C/V | igual |",
        "|---|---|---|---|---|---|",
    ]
    async with httpx.AsyncClient() as http:
        rest = ClienteRestBinance(args.rest, http)
        for s in simbolos:
            negocios = gravados[s]
            buracos = lacunas_de_id(negocios)
            if buracos:
                # Queda do stream: ressincroniza pelo REST, como o processo de ticks faz.
                extras = await rest.agg_trades(s, inicio, fim)
                vistos = {n.id for n in negocios}
                negocios += [n for n in extras if n.id not in vistos]
                print(f"{s}: {len(buracos)} lacunas de id preenchidas pelo REST", flush=True)
            p5 = fim - _5M
            antes = await rest.klines(s, IntervaloColeta.M1, p5, inicio) if p5 < inicio else []
            k1 = [
                _kline(x)
                for x in await rest._get(  # noqa: SLF001
                    "/api/v3/klines",
                    {
                        "symbol": s,
                        "interval": "1m",
                        "startTime": str(inicio),
                        "endTime": str(fim - 1),
                        "limit": "1000",
                    },
                )
            ]
            k5 = _kline(
                (
                    await rest._get(  # noqa: SLF001
                        "/api/v3/klines",
                        {
                            "symbol": s,
                            "interval": "5m",
                            "startTime": str(p5),
                            "endTime": str(fim - 1),
                            "limit": "1",
                        },
                    )
                )[0]
            )
            linhas, ok = comparar(s, negocios, antes, k1, k5)
            ok_geral &= ok
            print(f"{s}: {len(negocios)} aggTrades, {len(linhas)} velas, igual={ok}", flush=True)
            for linha in linhas:
                nosso = "/".join(map(str, linha.nosso)) if linha.nosso else "—"
                binance = "/".join(map(str, linha.binance))
                saida.append(
                    f"| {s} | {linha.tg} | {linha.t} | {nosso} | {binance} | "
                    f"{'sim' if linha.igual else 'NÃO'} |"
                )
    texto = "\n".join(saida) + "\n"
    print(texto)
    with open(args.saida, "w") as f:
        f.write(texto)
    print(json.dumps({"igual": ok_geral}))
    return 0 if ok_geral else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(asyncio.run(principal()))
