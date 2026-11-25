"""Conferência da agregação local contra os candles oficiais da Binance.

Execução (dentro do contêiner do coletor): ``python -m sinais.dados.conferencia``.
Compara as últimas 6 horas de 5m e 1h e sai com código 1 se houver divergência.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from decimal import Decimal

from sinais.core.dominio import TempoGrafico
from sinais.core.tempo import InstanteMs
from sinais.dados.modelos import Candle

_CAMPOS = ("abertura_preco", "maxima", "minima", "fechamento", "volume", "negocios")


@dataclass(frozen=True, slots=True)
class Divergencia:
    abertura: InstanteMs
    campo: str
    oficial: Decimal | int | None
    nosso: Decimal | int | None


def comparar(oficiais: Sequence[Candle], nossos: Sequence[Candle]) -> list[Divergencia]:
    por_abertura = {c.abertura: c for c in nossos}
    saida: list[Divergencia] = []
    for o in oficiais:
        n = por_abertura.get(o.abertura)
        if n is None:
            saida.append(Divergencia(o.abertura, "ausente", None, None))
            continue
        for campo in _CAMPOS:
            vo, vn = getattr(o, campo), getattr(n, campo)
            if vo != vn:
                saida.append(Divergencia(o.abertura, campo, vo, vn))
    return saida


async def _principal() -> int:  # pragma: no cover - ligação de I/O, roda no teste de fumaça
    import httpx
    from sqlalchemy.ext.asyncio import create_async_engine

    from sinais.core.config import carregar_configuracao
    from sinais.core.dominio import ATIVOS_V1
    from sinais.core.tempo import RelogioSistema
    from sinais.dados.agregacao import agregar
    from sinais.dados.modelos import IntervaloColeta
    from sinais.dados.provedores.binance.parsing import de_linha_rest
    from sinais.persistencia.repositorio_pg import RepositorioCandlesPg
    from sinais.persistencia.url import url_async

    cfg = carregar_configuracao()
    repo = RepositorioCandlesPg(create_async_engine(url_async(cfg.database_url.get_secret_value())))
    agora = RelogioSistema().agora_ms()
    total = 0
    async with httpx.AsyncClient(base_url=cfg.binance_rest_url, timeout=10) as http:
        for ativo in ATIVOS_V1:
            for tg in (TempoGrafico.M5, TempoGrafico.H1):
                fim = agora - agora % tg.duracao_ms
                inicio = fim - 6 * 3_600_000
                r = await http.get(
                    "/api/v3/klines",
                    params={
                        "symbol": ativo.simbolo_provedor,
                        "interval": tg.value,
                        "startTime": inicio,
                        "endTime": fim - 1,
                    },
                )
                r.raise_for_status()
                oficiais = [
                    _como(de_linha_rest(ativo.simbolo, IntervaloColeta.M1, linha), tg)
                    for linha in r.json()
                ]
                minutos = await repo.listar(ativo.simbolo, IntervaloColeta.M1, inicio, fim)
                divergencias = comparar(oficiais, agregar(minutos, tg))
                total += len(divergencias)
                print(
                    f"{ativo.simbolo} {tg.value}: {len(oficiais)} oficiais, "
                    f"{len(divergencias)} divergências"
                )
                for d in divergencias[:5]:
                    print("  ", d)
    return 1 if total else 0


def _como(c: Candle, tg: TempoGrafico) -> Candle:  # pragma: no cover
    """O parser de 1m serve para 5m/1h (aberturas múltiplas de 1 min); só troca a duração."""
    return replace(c, intervalo_ms=tg.duracao_ms, fonte="agregado")


if __name__ == "__main__":  # pragma: no cover
    import asyncio
    import sys

    sys.exit(asyncio.run(_principal()))
