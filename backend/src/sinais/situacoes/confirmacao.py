"""Confirmação em meses novos (design §9b.2; pré-registro §7).

Uso (depois de cada mês fechado e publicado na Binance)::

    python -m sinais.situacoes.confirmacao --candidatas docs/laboratorio/situacoes-candidatas.json

Cada execução reprocessa, com o mesmo código e os mesmos parâmetros da descoberta, a série de 1m
que começa em 2026-10 (mês só de aquecimento) e vai até o último mês fechado; contam os sinais
com decisão a partir de 2026-11. Como os detectores são causais e a série começa sempre no mesmo
ponto, o resultado de um mês não muda quando meses novos entram: o acumulado é reproduzível.

Critério por candidata: n ≥ 100 operações decididas não sobrepostas e Wilson inferior > p*;
Benjamini-Hochberg (q = 0,05) sobre as candidatas (família própria). Cada sinal sai também como
``RegistroSinal`` (o mesmo registro da área de sinais). Candidatas da camada B ficam pendentes:
a confirmação delas exige congelar o modelo e ainda não foi implementada (só faz sentido se
alguma B for aprovada na descoberta).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from sinais.analise.indicadores import atr
from sinais.backtest.metricas import benjamini_hochberg, calcular
from sinais.backtest.precos import SeriePrecos
from sinais.corretoras.regras import RegraVencimento
from sinais.situacoes.liquidacao import RegistroSinal, registros_de
from sinais.situacoes.motor import detectar_todas
from sinais.situacoes.parametros import MINUTO_MS, N_ATR, N_MINIMO_CONFIRMACAO, Q_BH
from sinais.situacoes.simulacao import simular_eventos

PRIMEIRO_MES_NOVO = "2026-11"
MES_AQUECIMENTO = "2026-10"
Chave = tuple[str, str, str, str, str]  # ativo, variação, espelho, expiração, camada


def _chave(c: Mapping[str, Any]) -> Chave:
    return (c["ativo"], c["variacao"], c["espelho"], c["expiracao"], c["camada"])


def meses_fechados(primeiro: str, hoje: str) -> list[str]:
    """Meses de ``primeiro`` até o último mês já encerrado em ``hoje`` (AAAA-MM-DD)."""
    a, m = (int(x) for x in primeiro.split("-"))
    ha, hm = (int(x) for x in hoje.split("-")[:2])
    saida = []
    while (a, m) < (ha, hm):
        saida.append(f"{a:04d}-{m:02d}")
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)
    return saida


@dataclass
class ConfirmacaoAtivo:
    ativo: str
    operacoes: dict[Chave, pd.DataFrame] = field(default_factory=dict)
    registros: dict[Chave, list[RegistroSinal]] = field(default_factory=dict)


@dataclass(frozen=True)
class LinhaConfirmacao:
    chave: Chave
    n: int
    taxa: float
    wilson_inf: float
    pvalor: float
    passou_bh: bool
    status: str


def avaliar_confirmacao(
    ativo: str,
    df_1m: pd.DataFrame,
    precos_1s: SeriePrecos,
    candidatas: Sequence[Mapping[str, Any]],
    regras: Mapping[str, RegraVencimento],
    inicio: int,
) -> ConfirmacaoAtivo:
    """Sinais das candidatas deste ativo com decisão ≥ ``inicio`` (camada A)."""
    minhas = [c for c in candidatas if c["ativo"] == ativo]
    saida = ConfirmacaoAtivo(ativo)
    if not minhas:
        return saida
    ev = detectar_todas(df_1m)
    ev = ev[~ev["conflito"] & (ev["decisao"] >= inicio)]
    decisoes = df_1m.index.to_numpy(dtype="int64") + MINUTO_MS
    atr_dec = pd.Series(atr(df_1m, N_ATR).to_numpy(dtype="float64"), index=decisoes)
    for c in minhas:
        k = _chave(c)
        if c["camada"] != "A":
            saida.operacoes[k] = pd.DataFrame(columns=["resultado"])
            saida.registros[k] = []
            continue
        sel = ev[(ev["variacao"] == c["variacao"]) & (ev["espelho"] == c["espelho"])]
        regra = regras[c["expiracao"]]
        ops = simular_eventos(sel, precos_1s, regra, atr_dec)
        exp_min = regra.grade_ms // MINUTO_MS
        situacao = sel["situacao"].iloc[0] if len(sel) else c["variacao"]
        saida.operacoes[k] = ops
        saida.registros[k] = registros_de(ops, ativo, situacao, c["variacao"], exp_min, precos_1s)
    return saida


def consolidar_confirmacao(
    por_ativo: Sequence[ConfirmacaoAtivo], payout: float, q: float = Q_BH
) -> list[LinhaConfirmacao]:
    chaves: list[Chave] = []
    metricas = []
    for r in por_ativo:
        for k, ops in r.operacoes.items():
            chaves.append(k)
            metricas.append(None if k[4] != "A" else calcular(ops, payout))
    pv = [1.0 if m is None or math.isnan(m.pvalor) else m.pvalor for m in metricas]
    bh = benjamini_hochberg(pv, q) if pv else []
    linhas = []
    for k, m, p, passou in zip(chaves, metricas, pv, bh, strict=True):
        if m is None:
            linhas.append(
                LinhaConfirmacao(k, 0, math.nan, math.nan, 1.0, False, "pendente (camada B)")
            )
            continue
        n = m.wins + m.losses
        if n < N_MINIMO_CONFIRMACAO:
            status = "em andamento"
        elif m.wilson_inf > m.p_equilibrio and passou:
            status = "confirmada"
        else:
            status = "não confirmada"
        linhas.append(LinhaConfirmacao(k, n, m.taxa, m.wilson_inf, p, bool(passou), status))
    return linhas


def markdown_confirmacao(
    linhas: Sequence[LinhaConfirmacao], por_ativo: Sequence[ConfirmacaoAtivo], meses: Sequence[str]
) -> str:
    def pct(x: float) -> str:
        return "—" if math.isnan(x) else f"{100 * x:.2f}%"

    partes = [
        "# Confirmação em meses novos — Motor de Situações",
        "",
        f"Meses: {', '.join(meses) or 'nenhum mês novo fechado ainda'}. Critério: n ≥ "
        f"{N_MINIMO_CONFIRMACAO} e Wilson inferior > equilíbrio; BH sobre as candidatas.",
        "",
        "| Ativo | Variação | Espelho | Exp. | Camada | n | Taxa | Wilson inf. | p | BH | Status |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for x in linhas:
        a, v, e, exp, cam = x.chave
        partes.append(
            f"| {a} | {v} | {e} | {exp} | {cam} | {x.n} | {pct(x.taxa)} | {pct(x.wilson_inf)} "
            f"| {x.pvalor:.2g} | {'sim' if x.passou_bh else 'não'} | **{x.status}** |"
        )
    partes += [
        "",
        "## Sinais liquidados",
        "",
        "| Sinal | Situação | Entrada | Preço de entrada | Vencimento | Preço final | Resultado |",
        "|---|---|---|---|---|---|---|",
    ]

    def hora(t: int) -> str:
        return datetime.fromtimestamp(t / 1000, UTC).strftime("%Y-%m-%d %H:%M:%S")

    for r in por_ativo:
        for regs in r.registros.values():
            for s in regs:
                partes.append(
                    f"| {s.titulo} | {s.variacao} | {hora(s.entrada_t)} | {s.preco_entrada} "
                    f"| {hora(s.vencimento_t)} | {s.preco_final} | {s.resultado} |"
                )
    return "\n".join(partes) + "\n"


async def _principal(  # pragma: no cover - rede
    candidatas_arq: Path, payout: float, primeiro: str, ate: str | None, aquecimento: str
) -> None:
    import httpx
    import numpy as np

    from sinais.backtest.historico import baixar_meses
    from sinais.modelos.dados_1s import baixar_mes_1s
    from sinais.situacoes.periodos import inicio_mes
    from sinais.situacoes.relatorio import REGRAS

    hoje = datetime.now(UTC).strftime("%Y-%m-%d")
    meses = meses_fechados(primeiro, hoje)
    if ate is not None:
        meses = [m for m in meses if m <= ate]
    candidatas = json.loads(candidatas_arq.read_text(encoding="utf-8"))
    if not meses:
        print("Nenhum mês novo fechado ainda: nada a confirmar.", flush=True)
        return
    if not candidatas:
        print("Nenhuma candidata na descoberta: família de confirmação vazia.", flush=True)
    serie = [tuple(int(x) for x in m.split("-")) for m in [aquecimento, *meses]]
    por_ativo = []
    async with httpx.AsyncClient() as http:
        for ativo in sorted({c["ativo"] for c in candidatas}):
            df_1m, lacunas = await baixar_meses(http, ativo, "1m", serie)  # type: ignore[arg-type]
            ts, cs = [], []
            for m in meses:
                ano, mes = (int(x) for x in m.split("-"))
                df_1s = await baixar_mes_1s(http, ativo, ano, mes)
                if df_1s is None:
                    lacunas.append(f"{ativo} 1s {m}")
                    continue
                ts.append(df_1s.index.to_numpy(dtype="int64"))
                cs.append(df_1s["c"].to_numpy(dtype="float64"))
            t, c = np.concatenate(ts), np.concatenate(cs)
            print(f"{ativo}: {len(df_1m)} min, {len(t)} s; lacunas: {lacunas or 'nenhuma'}")
            precos = SeriePrecos(t, c, c, 1000)
            por_ativo.append(
                avaliar_confirmacao(ativo, df_1m, precos, candidatas, REGRAS, inicio_mes(meses[0]))
            )
    linhas = consolidar_confirmacao(por_ativo, payout)
    print(markdown_confirmacao(linhas, por_ativo, meses), flush=True)


if __name__ == "__main__":  # pragma: no cover
    a = argparse.ArgumentParser()
    a.add_argument(
        "--candidatas", type=Path, default=Path("../docs/laboratorio/situacoes-candidatas.json")
    )
    a.add_argument("--payout", type=float, default=0.86)
    a.add_argument("--primeiro", default=PRIMEIRO_MES_NOVO, help="só para teste de fumaça")
    a.add_argument("--aquecimento", default=MES_AQUECIMENTO, help="só para teste de fumaça")
    a.add_argument("--ate", default=None, help="último mês (AAAA-MM), opcional")
    x = a.parse_args()
    asyncio.run(_principal(x.candidatas, x.payout, x.primeiro, x.ate, x.aquecimento))
