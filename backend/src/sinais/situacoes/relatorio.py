"""Rodadas reais do motor de situações (GitHub Actions), com relatório impresso no log.

Uso::

    python -m sinais.situacoes.relatorio --modo contagem --ativo BTCUSDT --fim 2026-10 --meses 24
    python -m sinais.situacoes.relatorio --modo avaliacao --ativo BTCUSDT ...

``contagem`` só usa 1m e não olha preço futuro nenhum (pré-registro §4). ``avaliacao`` baixa também
o 1 s, simula e avalia as camadas A e B (pré-registro §5).
"""

from __future__ import annotations

import argparse
import asyncio
import time
from pathlib import Path

from sinais.core.dominio import Expiracao
from sinais.corretoras.regras import EXNOVA, RegraVencimento
from sinais.situacoes.periodos import Periodos, periodos_descoberta

EXPIRACOES: dict[str, Expiracao] = {"15m": Expiracao.M15, "5m": Expiracao.M5, "30m": Expiracao.M30}
REGRAS: dict[str, RegraVencimento] = {k: EXNOVA.regras[e] for k, e in EXPIRACOES.items()}


def _meses(p: Periodos) -> list[tuple[int, int]]:
    from sinais.backtest.walk_forward import _somar_meses
    from sinais.core.tempo import para_datetime

    saida = []
    t = p.inicio
    while t < p.fim:
        dt = para_datetime(t)
        saida.append((dt.year, dt.month))
        t = _somar_meses(t, 1)
    return saida


async def _contagem(
    ativos: list[str], fim: str, meses: int, saida: Path
) -> None:  # pragma: no cover
    import httpx
    import pandas as pd

    from sinais.backtest.historico import baixar_meses
    from sinais.situacoes.contagem import markdown_contagem, tabela_contagem
    from sinais.situacoes.motor import detectar_todas

    inicio_total = time.monotonic()
    p = periodos_descoberta(fim, meses)
    partes = []
    async with httpx.AsyncClient() as http:
        for ativo in ativos:
            df, lacunas = await baixar_meses(http, ativo, "1m", _meses(p))
            print(f"{ativo}: {len(df)} candles de 1m; lacunas: {lacunas or 'nenhuma'}", flush=True)
            ev = detectar_todas(df)
            print(f"{ativo}: {len(ev)} eventos ({(time.monotonic() - inicio_total) / 60:.1f} min)")
            partes.append(ev.assign(ativo=ativo))
    eventos = pd.concat(partes, ignore_index=True)
    periodos = {"teste": p.teste, "holdout": p.holdout, "total": (p.inicio, p.fim)}
    tab = tabela_contagem(eventos, periodos, REGRAS, ativos)
    conflitos = int(eventos["conflito"].sum())
    texto = "\n".join(
        [
            f"# Contagem de ocorrências (sem rótulo) — {', '.join(ativos)}",
            "",
            f"Período: {_meses(p)[0]} a {_meses(p)[-1]}; teste = 14 meses do walk-forward; "
            f"eventos brutos: {len(eventos)}; em conflito (fora): {conflitos}.",
            "",
            markdown_contagem(tab, list(periodos)),
            "",
            f"Elegíveis (teste ≥ 300): {int(tab['elegivel'].sum())} de {len(tab)}.",
            f"Tempo: {(time.monotonic() - inicio_total) / 60:.1f} min.",
        ]
    )
    saida.mkdir(parents=True, exist_ok=True)
    (saida / "contagem.md").write_text(texto, encoding="utf-8")
    tab.to_csv(saida / "contagem.csv", index=False)
    print(texto, flush=True)


if __name__ == "__main__":  # pragma: no cover
    a = argparse.ArgumentParser()
    a.add_argument("--modo", choices=["contagem", "avaliacao"], required=True)
    a.add_argument("--ativo", action="append", default=None)
    a.add_argument("--fim", default="2026-10")
    a.add_argument("--meses", type=int, default=24)
    a.add_argument("--payout", type=float, default=0.86)
    a.add_argument("--saida", type=Path, default=Path("relatorio"))
    args = a.parse_args()
    ativos = args.ativo or ["BTCUSDT", "ETHUSDT"]
    if args.modo == "contagem":
        asyncio.run(_contagem(ativos, args.fim, args.meses, args.saida))
    else:
        raise SystemExit("modo avaliacao: ainda não implementado")
