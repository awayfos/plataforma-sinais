"""Laboratório: baixa o histórico oficial e avalia as estratégias simples com as regras da
Exnova em cada expiração. Uso: ``python -m sinais.backtest.laboratorio --meses 24``."""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from sinais.backtest import baselines
from sinais.backtest.metricas import calcular
from sinais.backtest.precos import SeriePrecos
from sinais.backtest.relatorio import LinhaRelatorio, gerar_json, gerar_markdown
from sinais.backtest.simulador import simular
from sinais.corretoras.regras import EXNOVA, ponto_equilibrio

_MINUTO_MS = 60_000
_MES_MS = 30 * 86_400_000

ESTRATEGIAS: dict[str, Callable[[pd.DataFrame], pd.DataFrame]] = {
    "sempre_compra": baselines.sempre_compra,
    "sempre_venda": baselines.sempre_venda,
    "seguir_ultimo": baselines.seguir_ultimo,
    "aleatoria": lambda df: baselines.aleatoria(df, semente=42),
}


def _meses_acima(ops: pd.DataFrame, p_eq: float) -> float:
    decididas = ops[ops["resultado"].isin(["WIN", "LOSS"])]
    if decididas.empty:
        return float("nan")
    mes = decididas["entrada_t"] // _MES_MS
    taxas = decididas.assign(w=decididas["resultado"] == "WIN").groupby(mes)["w"].mean()
    return float((taxas > p_eq).mean())


def avaliar(df_1m: pd.DataFrame, ativo: str, payout: float) -> list[LinhaRelatorio]:
    precos = SeriePrecos.de_quadro(df_1m, _MINUTO_MS)
    linhas = []
    for expiracao, regra in EXNOVA.regras.items():
        for nome, estrategia in ESTRATEGIAS.items():
            ops = simular(estrategia(df_1m), precos, regra)
            m = calcular(ops, payout)
            linhas.append(
                LinhaRelatorio(
                    ativo,
                    f"{int(expiracao) // 60}m",
                    nome,
                    m,
                    _meses_acima(ops, ponto_equilibrio(payout)),
                )
            )
    return linhas


def _ultimos_meses(n: int) -> list[tuple[int, int]]:
    hoje = datetime.now(UTC)
    total = hoje.year * 12 + hoje.month - 1 - 1  # último mês completo
    return [((total - i) // 12, (total - i) % 12 + 1) for i in range(n)][::-1]


async def _principal(meses: int, payout: float, saida: Path) -> None:  # pragma: no cover
    import httpx

    from sinais.backtest.historico import baixar_meses

    linhas: list[LinhaRelatorio] = []
    todas_lacunas: list[str] = []
    periodo = _ultimos_meses(meses)
    async with httpx.AsyncClient() as http:
        for ativo in ("BTCUSDT", "ETHUSDT"):
            df, lacunas = await baixar_meses(http, ativo, "1m", periodo)
            todas_lacunas += lacunas
            print(f"{ativo}: {len(df)} candles de 1m, lacunas: {lacunas or 'nenhuma'}")
            linhas += avaliar(df, ativo, payout)
    hipoteses = {
        "fonte": f"data.binance.vision, klines de 1m, {periodo[0]} a {periodo[-1]}",
        "payout": f"{payout} (hipotético até o cliente informar o da Exnova)",
        "preço": "1m: entrada = abertura do minuto da decisão; vencimento = preço na fronteira",
        "latência": "2 s (checada contra o prazo de compra)",
        "cortes 5m/30m/1h": "hipóteses (1/3 da grade) até confirmar na Exnova",
        "lacunas": ", ".join(todas_lacunas) or "nenhuma",
    }
    saida.mkdir(parents=True, exist_ok=True)
    (saida / "relatorio.md").write_text(gerar_markdown(linhas, hipoteses), encoding="utf-8")
    (saida / "relatorio.json").write_text(gerar_json(linhas, hipoteses), encoding="utf-8")
    print((saida / "relatorio.md").read_text(encoding="utf-8"))


if __name__ == "__main__":  # pragma: no cover
    p = argparse.ArgumentParser()
    p.add_argument("--meses", type=int, default=24)
    p.add_argument("--payout", type=float, default=0.85)
    p.add_argument("--saida", type=Path, default=Path("relatorio"))
    a = p.parse_args()
    asyncio.run(_principal(a.meses, a.payout, a.saida))
