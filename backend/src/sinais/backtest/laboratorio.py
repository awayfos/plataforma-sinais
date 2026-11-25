"""Laboratório: baixa o histórico oficial e avalia as estratégias simples com as regras da
Exnova em cada expiração. Uso: ``python -m sinais.backtest.laboratorio --meses 24``."""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from sinais.backtest import baselines
from sinais.backtest.metricas import calcular
from sinais.backtest.precos import SeriePrecos
from sinais.backtest.relatorio import LinhaRelatorio, gerar_json, gerar_markdown
from sinais.backtest.simulador import simular
from sinais.core.dominio import Expiracao
from sinais.corretoras.regras import EXNOVA, ponto_equilibrio

_MINUTO_MS = 60_000
_MES_MS = 30 * 86_400_000

ESTRATEGIAS: dict[str, Callable[[pd.DataFrame], pd.DataFrame]] = {
    "sempre_compra": baselines.sempre_compra,
    "sempre_venda": baselines.sempre_venda,
    "seguir_ultimo": baselines.seguir_ultimo,
    "aleatoria": lambda df: baselines.aleatoria(df, semente=42),
}


def meses_acima(ops: pd.DataFrame, p_eq: float, minimo: int = 30) -> float:
    """Fração dos meses civis (UTC) com taxa acima de ``p_eq``; meses com menos de ``minimo``
    operações decididas não contam."""
    decididas = ops[ops["resultado"].isin(["WIN", "LOSS"])]
    if decididas.empty:
        return float("nan")
    mes = pd.to_datetime(decididas["entrada_t"], unit="ms").dt.to_period("M")
    g = (decididas["resultado"] == "WIN").groupby(mes)
    taxas = g.mean()[g.size() >= minimo]
    return float((taxas > p_eq).mean()) if len(taxas) else float("nan")


def avaliar(
    df_1m: pd.DataFrame,
    ativo: str,
    payout: float,
    df_1s: pd.DataFrame | None = None,
    expiracoes: Sequence[Expiracao] | None = None,
) -> list[LinhaRelatorio]:
    """Com ``df_1s``, liquida com preços de 1 s e entrada sorteada na janela de compra
    (realista); sem ele, usa 1 min (limite superior otimista para expirações curtas)."""
    precos = (
        SeriePrecos.de_quadro(df_1s, 1000)
        if df_1s is not None
        else SeriePrecos.de_quadro(df_1m, _MINUTO_MS)
    )
    rotulo = " (1s)" if df_1s is not None else ""
    linhas = []
    for expiracao in expiracoes or list(EXNOVA.regras):
        regra = EXNOVA.regras[expiracao]
        for nome, estrategia in ESTRATEGIAS.items():
            ops = simular(
                estrategia(df_1m), precos, regra, entrada_aleatoria=df_1s is not None, semente=7
            )
            m = calcular(ops, payout)
            linhas.append(
                LinhaRelatorio(
                    ativo,
                    f"{int(expiracao) // 60}m{rotulo}",
                    nome,
                    m,
                    meses_acima(ops, ponto_equilibrio(payout)),
                )
            )
    return linhas


def _mes(am: tuple[int, int]) -> str:
    return f"{am[0]:04d}-{am[1]:02d}"


def _ultimos_meses(n: int) -> list[tuple[int, int]]:
    hoje = datetime.now(UTC)
    total = hoje.year * 12 + hoje.month - 1 - 1  # último mês completo
    return [((total - i) // 12, (total - i) % 12 + 1) for i in range(n)][::-1]


async def _principal(  # pragma: no cover
    meses: int, payout: float, saida: Path, meses_1s: int
) -> None:
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
            if meses_1s:
                recentes = periodo[-meses_1s:]
                df_1s, lac_1s = await baixar_meses(http, ativo, "1s", recentes)
                todas_lacunas += lac_1s
                inicio_1s = int(df_1s.index.min()) if len(df_1s) else 0
                print(f"{ativo}: {len(df_1s)} candles de 1s ({recentes[0]} a {recentes[-1]})")
                linhas += avaliar(
                    df[df.index >= inicio_1s],
                    ativo,
                    payout,
                    df_1s=df_1s,
                    expiracoes=[Expiracao.M1, Expiracao.M5],
                )
                del df_1s
    hipoteses = {
        "fonte": f"data.binance.vision, klines de 1m, {_mes(periodo[0])} a {_mes(periodo[-1])}"
        + (f"; 1s nos últimos {meses_1s} meses" if meses_1s else ""),
        "payout": f"{payout} (hipotético até o cliente informar o da Exnova)",
        "preço (linhas sem '(1s)')": "1m: entrada = abertura do minuto da decisão, sem "
        "latência; LIMITE SUPERIOR otimista para expirações curtas",
        "preço (linhas '(1s)')": "1s: entrada sorteada entre decisão + 2 s e o prazo de "
        "compra; vencimento = fechamento do candle de 1 s que termina no vencimento",
        "apertado": "diferença de preço menor que 0,01% do preço (a corretora pode divergir)",
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
    p.add_argument("--meses-1s", type=int, default=2)
    a = p.parse_args()
    asyncio.run(_principal(a.meses, a.payout, a.saida, a.meses_1s))
