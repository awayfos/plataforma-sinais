"""Relatório de decisão da Fase 6 (design §13.3): por ativo × expiração, ligar ou não.

Uso: ``python -m sinais.modelos.decisao --meses 24 --payout 0.85 --saida relatorio``.
"""

from __future__ import annotations

import argparse
import asyncio
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from sinais.backtest.metricas import Metricas, benjamini_hochberg, calcular
from sinais.backtest.precos import SeriePrecos
from sinais.backtest.simulador import simular
from sinais.core.dominio import Expiracao
from sinais.corretoras.regras import RegraVencimento, ponto_equilibrio
from sinais.modelos.avaliacao import ResultadoCombinacao

N_MINIMO = 300
N_MINIMO_HOLDOUT = 100
MARGEM = 0.01
MINIMO_MES = 30


def meses_acima_estrito(ops: pd.DataFrame, p_eq: float, meses_testados: int) -> float:
    """Fração de TODOS os meses testados com 30+ operações e taxa acima de ``p_eq``.
    Mês sem operações (ou pulado) conta como abaixo: impede concentrar o resultado."""
    if meses_testados <= 0:
        return math.nan
    decididas = ops[ops["resultado"].isin(["WIN", "LOSS"])]
    if decididas.empty:
        return 0.0
    mes = pd.to_datetime(decididas["entrada_t"], unit="ms").dt.to_period("M")
    g = (decididas["resultado"] == "WIN").groupby(mes)
    acima = ((g.mean() > p_eq) & (g.size() >= MINIMO_MES)).sum()
    return float(acima) / meses_testados


@dataclass(frozen=True)
class LinhaDecisao:
    ativo: str
    expiracao: str
    fora_amostra: Metricas
    holdout: Metricas
    melhor_baseline: float
    meses_acima: float
    ece: float
    dobras: int
    recomendacao: str
    motivo: str


def consolidar(
    resultados: Mapping[tuple[str, Expiracao], ResultadoCombinacao], payout: float
) -> list[LinhaDecisao]:
    p_eq = ponto_equilibrio(payout)
    chaves = list(resultados)
    metricas = [calcular(resultados[k].operacoes, payout) for k in chaves]
    pv = [1.0 if math.isnan(m.pvalor) else m.pvalor for m in metricas]
    bh = benjamini_hochberg(pv)
    linhas = []
    for (ativo, exp), m, passou_bh in zip(chaves, metricas, bh, strict=True):
        r = resultados[(ativo, exp)]
        h = calcular(r.holdout, payout)
        bases = [calcular(o, payout).taxa for o in r.baselines.values()]
        melhor = max((b for b in bases if not math.isnan(b)), default=math.nan)
        meses = meses_acima_estrito(r.operacoes, p_eq, r.meses_testados)
        motivos = []
        if m.wins + m.losses < N_MINIMO:
            motivos.append(f"só {m.wins + m.losses} operações decididas (mínimo {N_MINIMO})")
        if not (m.wilson_inf > p_eq + MARGEM):
            motivos.append("limite inferior de Wilson não supera o equilíbrio + 1 p.p.")
        if not (m.taxa > melhor):
            motivos.append("não supera as estratégias simples")
        if not (meses >= 0.7):
            motivos.append("menos de 70% dos meses testados acima do equilíbrio")
        if not passou_bh:
            motivos.append("não sobrevive à correção de Benjamini-Hochberg")
        if h.wins + h.losses < N_MINIMO_HOLDOUT or not (h.wilson_inf > p_eq):
            motivos.append(
                f"holdout sem confirmação (mínimo {N_MINIMO_HOLDOUT} operações e Wilson "
                "inferior acima do equilíbrio)"
            )
        linhas.append(
            LinhaDecisao(
                ativo,
                f"{int(exp) // 60}m",
                m,
                h,
                melhor,
                meses,
                r.ece_medio,
                r.dobras,
                "ligar" if not motivos else "não ligar",
                "; ".join(motivos) or "passou em todos os critérios",
            )
        )
    return linhas


def validar_com_1s(
    sinais: pd.DataFrame, precos_1s: SeriePrecos, regra: RegraVencimento, payout: float
) -> tuple[Metricas, bool]:
    """Re-simula os sinais do holdout com preços de 1 s e entrada sorteada na janela de compra
    (como um usuário real). Confirma só com 100+ operações e Wilson inferior acima do
    equilíbrio."""
    ops = simular(sinais, precos_1s, regra, entrada_aleatoria=True, semente=7)
    m = calcular(ops, payout)
    ok = m.wins + m.losses >= N_MINIMO_HOLDOUT and m.wilson_inf > m.p_equilibrio
    return m, bool(ok)


def _pct(x: float) -> str:
    return "—" if math.isnan(x) else f"{100 * x:.2f}%"


def gerar_markdown_decisao(linhas: list[LinhaDecisao], hipoteses: Mapping[str, str]) -> str:
    partes = ["# Relatório de decisão — modelos", "", "## Hipóteses e fonte", ""]
    partes += [f"- **{k}:** {v}" for k, v in hipoteses.items()]
    partes += [
        "",
        "## Resultado por ativo e expiração (fora da amostra)",
        "",
        "| Ativo | Exp. | Operações | Taxa | Wilson inf. | Equilíbrio | Melhor simples "
        "| Meses acima | Holdout | ECE | Dobras | Recomendação | Motivo |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for x in linhas:
        m = x.fora_amostra
        partes.append(
            f"| {x.ativo} | {x.expiracao} | {m.wins + m.losses} | {_pct(m.taxa)} "
            f"| {_pct(m.wilson_inf)} | {_pct(m.p_equilibrio)} | {_pct(x.melhor_baseline)} "
            f"| {_pct(x.meses_acima)} | {_pct(x.holdout.taxa)} | {_pct(x.ece)} | {x.dobras} "
            f"| **{x.recomendacao}** | {x.motivo} |"
        )
    ligadas = [f"{x.ativo} {x.expiracao}" for x in linhas if x.recomendacao == "ligar"]
    partes += [
        "",
        "## Conclusão",
        "",
        (
            f"Combinações aprovadas: {', '.join(ligadas)}."
            if ligadas
            else "Nenhuma combinação passou nos critérios. Pela regra do produto, todas "
            "mostram AGUARDAR até que um modelo seja aprovado."
        ),
        "",
    ]
    return "\n".join(partes)


async def _principal(meses: int, payout: float, saida: Path) -> None:  # pragma: no cover
    import gc

    import httpx

    from sinais.backtest.historico import baixar_meses
    from sinais.backtest.laboratorio import _mes, _ultimos_meses
    from sinais.modelos.avaliacao import avaliar_combinacao
    from sinais.modelos.blocos import montar_snapshot_em_blocos

    periodo = _ultimos_meses(meses)
    resultados: dict[tuple[str, Expiracao], ResultadoCombinacao] = {}
    async with httpx.AsyncClient() as http:
        for ativo in ("BTCUSDT", "ETHUSDT"):
            df, lacunas = await baixar_meses(http, ativo, "1m", periodo)
            print(f"{ativo}: {len(df)} candles; lacunas: {lacunas or 'nenhuma'}", flush=True)
            snapshot = montar_snapshot_em_blocos(df)
            print(f"{ativo}: snapshot {snapshot.shape}", flush=True)
            for exp in Expiracao:
                r = avaliar_combinacao(df, snapshot, exp, payout)
                resultados[(ativo, exp)] = r
                print(f"{ativo} {exp.name}: {r.dobras} dobras, avisos {r.avisos}", flush=True)
            del snapshot
            gc.collect()
    hipoteses = {
        "fonte": f"data.binance.vision, 1m, {_mes(periodo[0])} a {_mes(periodo[-1])}",
        "modelo": "HistGradientBoosting (scikit-learn) + calibração isotônica, features fs-1",
        "walk-forward": "treino 6 meses (1 a cada 3 minutos) → calibração 1 mês → teste 1 "
        "mês; purga pelo vencimento real e embargo de 1 h; holdout final de 3 meses",
        "decisão": "COMPRA se p ≥ equilíbrio + 1 p.p.; VENDA se p ≤ 1 − (equilíbrio + 1 p.p.)",
        "payout": f"{payout} (hipotético até o cliente informar o da Exnova)",
        "preço": "1m (entrada na abertura do minuto da decisão): limite superior otimista "
        "para 1m e 5m; combinações aprovadas são revalidadas com 1 s no holdout",
    }
    linhas = consolidar(resultados, payout)
    validacoes: list[str] = []
    aprovadas = [x for x in linhas if x.recomendacao == "ligar"]
    if aprovadas:
        from sinais.corretoras.regras import EXNOVA

        async with httpx.AsyncClient() as http:
            for x in aprovadas:
                exp = next(e for e in Expiracao if f"{int(e) // 60}m" == x.expiracao)
                df_1s, _ = await baixar_meses(http, x.ativo, "1s", periodo[-3:])
                m1s, ok = validar_com_1s(
                    resultados[(x.ativo, exp)].sinais_holdout,
                    SeriePrecos.de_quadro(df_1s, 1000),
                    EXNOVA.regras[exp],
                    payout,
                )
                del df_1s
                validacoes.append(
                    f"| {x.ativo} | {x.expiracao} | {m1s.wins + m1s.losses} | {_pct(m1s.taxa)} "
                    f"| {_pct(m1s.wilson_inf)} | {_pct(m1s.p_equilibrio)} | {m1s.apertados} "
                    f"| {_pct(m1s.taxa_sem_apertados)} "
                    f"| **{'confirmada' if ok else 'reprovada'}** |"
                )
    saida.mkdir(parents=True, exist_ok=True)
    texto = gerar_markdown_decisao(linhas, hipoteses)
    if validacoes:
        texto += "\n".join(
            [
                "## Validação realista do holdout com preços de 1 s",
                "",
                "Entrada sorteada entre decisão + 2 s e o prazo de compra; vencimento no "
                "fechamento do segundo. Só combinações confirmadas aqui seguem para a Fase 7.",
                "",
                "| Ativo | Exp. | Operações | Taxa | Wilson inf. | Equilíbrio | Apertados "
                "| Taxa s/ apertados | Resultado |",
                "|---|---|---|---|---|---|---|---|---|",
                *validacoes,
                "",
            ]
        )
    (saida / "decisao.md").write_text(texto, encoding="utf-8")
    print(texto)


if __name__ == "__main__":  # pragma: no cover
    p = argparse.ArgumentParser()
    p.add_argument("--meses", type=int, default=24)
    p.add_argument("--payout", type=float, default=0.85)
    p.add_argument("--saida", type=Path, default=Path("relatorio"))
    a = p.parse_args()
    asyncio.run(_principal(a.meses, a.payout, a.saida))
