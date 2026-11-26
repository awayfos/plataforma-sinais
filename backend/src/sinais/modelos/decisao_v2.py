"""Relatório de decisão do modelo v2 (Fase 6b): BTC e ETH, 1m e 5m, tudo com preços de 1 s.

Uso: ``python -m sinais.modelos.decisao_v2 --meses 24 --fim 2026-10 --payout 0.86 --saida rel``.

Baixa o 1m do período e o 1 s mês a mês (agrega a microestrutura e guarda só tempo e
fechamento de cada segundo), monta o ``fs-2`` e avalia com ``avaliar_combinacao_v2``. O
candidato à aprovação é ``fs-2 + filtro``; ``fs-2 sem filtro`` e ``fs-1 + filtro`` (rótulos de
1 s) são diagnósticos, sem direito a aprovação. Critérios: os mesmos da Fase 6 (``consolidar``).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from sinais.modelos.decisao import LinhaDecisao, _pct

ATIVOS = ("BTCUSDT", "ETHUSDT")
CANDIDATO = "fs-2 + filtro de apertados"


def meses_ate(fim: str, n: int) -> list[tuple[int, int]]:
    """Os ``n`` meses que terminam em ``fim`` (``AAAA-MM``), inclusive, em ordem."""
    ano, mes = (int(p) for p in fim.split("-"))
    total = ano * 12 + mes - 1
    return [((total - i) // 12, (total - i) % 12 + 1) for i in range(n)][::-1]


@dataclass(frozen=True)
class ExtrasFiltro:
    limiares: list[float]  # por dobra de teste; inf = sem filtro
    frac_filtrada: list[float]  # fração dos sinais do modelo cortada pelo filtro, por dobra
    limiar_holdout: float = math.nan
    frac_holdout: float = math.nan


def _cabecalho() -> list[str]:
    return [
        "| Ativo | Exp. | Operações | Taxa | Wilson inf. | Equilíbrio | Melhor simples "
        "| Meses acima | Apertados | Taxa s/ apertados | Holdout: operações | Holdout: taxa "
        "| Holdout: Wilson inf. | Holdout: apertados | ECE | Dobras | Recomendação | Motivo |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]


def _frac(a: int, n: int) -> str:
    return _pct(a / n) if n else "—"


def _linha(x: LinhaDecisao, rec: str) -> str:
    m, h = x.fora_amostra, x.holdout
    return (
        f"| {x.ativo} | {x.expiracao} | {m.wins + m.losses} | {_pct(m.taxa)} "
        f"| {_pct(m.wilson_inf)} | {_pct(m.p_equilibrio)} | {_pct(x.melhor_baseline)} "
        f"| {_pct(x.meses_acima)} | {_frac(m.apertados, m.n)} | {_pct(m.taxa_sem_apertados)} "
        f"| {h.wins + h.losses} | {_pct(h.taxa)} | {_pct(h.wilson_inf)} "
        f"| {_frac(h.apertados, h.n)} | {_pct(x.ece)} | {x.dobras} | {rec} | {x.motivo} |"
    )


def gerar_markdown_v2(
    linhas: Sequence[LinhaDecisao],
    diagnosticos: Mapping[str, Sequence[LinhaDecisao]],
    extras: Mapping[tuple[str, str], ExtrasFiltro],
    hipoteses: Mapping[str, str],
    diagnostico: str | None = None,
) -> str:
    """Com ``diagnostico`` (descrição da variação), o relatório inteiro é marcado como
    diagnóstico de sensibilidade: nenhuma linha é recomendação."""
    if diagnostico:
        partes = [
            "# DIAGNÓSTICO DE SENSIBILIDADE (sem direito a aprovação) — modelo v2 (Fase 6b)",
            "",
            f"Variação avaliada: {diagnostico}. Os critérios de aprovação são calculados só "
            "para leitura; nada aqui liga uma combinação.",
            "",
        ]
    else:
        partes = ["# Relatório de decisão — modelo v2 (Fase 6b)", ""]
    partes += ["## Hipóteses e fonte", ""]
    partes += [f"- **{k}:** {v}" for k, v in hipoteses.items()]
    partes += ["", f"## Resultado do candidato ({CANDIDATO})", "", *_cabecalho()]
    rec = "(teria: {})" if diagnostico else "**{}**"
    partes += [_linha(x, rec.format(x.recomendacao)) for x in linhas]
    partes += [
        "",
        "Apertados: fração das operações liquidadas com |Δ preço| ≤ 0,01%. Fora da amostra = "
        "dobras do walk-forward agregadas; holdout = últimos meses, avaliados uma vez.",
        "",
        "## Filtro de apertados (escolhido só na calibração)",
        "",
        "| Ativo | Exp. | Dobras de teste com filtro | Fração média cortada no teste "
        "| Limiares no teste | Limiar no holdout | Fração cortada no holdout |",
        "|---|---|---|---|---|---|---|",
    ]
    for (ativo, exp), e in extras.items():
        usados = sum(math.isfinite(v) for v in e.limiares)
        media = sum(e.frac_filtrada) / len(e.frac_filtrada) if e.frac_filtrada else math.nan
        lims = ", ".join("—" if not math.isfinite(v) else f"{v:.3f}" for v in e.limiares)
        lim_h = "—" if not math.isfinite(e.limiar_holdout) else f"{e.limiar_holdout:.3f}"
        partes.append(
            f"| {ativo} | {exp} | {usados} de {len(e.limiares)} | {_pct(media)} | {lims} "
            f"| {lim_h} | {_pct(e.frac_holdout)} |"
        )
    for nome, diag in diagnosticos.items():
        partes += [
            "",
            f"## Diagnóstico: {nome} (sem direito a aprovação)",
            "",
            "Mesmo walk-forward e mesmas janelas; serve só para entender o efeito de cada parte.",
            "",
            *_cabecalho(),
            *[_linha(x, f"(teria: {x.recomendacao})") for x in diag],
        ]
    ligadas = [f"{x.ativo} {x.expiracao}" for x in linhas if x.recomendacao == "ligar"]
    if diagnostico:
        conclusao = (
            "Diagnóstico de sensibilidade: não aprova nem reprova combinações. A configuração "
            "só pode ser aprovada na rodada confirmatória pré-registrada, em meses novos."
        )
    else:
        conclusao = (
            f"Combinações aprovadas: {', '.join(ligadas)}."
            if ligadas
            else "Nenhuma combinação passou nos critérios. Pela regra do produto, todas "
            "mostram AGUARDAR até que um modelo seja aprovado."
        )
    partes += ["", "## Conclusão", "", conclusao, ""]
    return "\n".join(partes)


def _json(
    linhas: Sequence[LinhaDecisao], diagnosticos: Mapping[str, Sequence[LinhaDecisao]]
) -> str:
    def conv(xs: Sequence[LinhaDecisao]) -> list[dict[str, object]]:
        return [asdict(x) for x in xs]

    dados = {"candidato": conv(linhas), **{k: conv(v) for k, v in diagnosticos.items()}}
    return json.dumps(dados, ensure_ascii=False, indent=2, default=str)


def _memoria_mb() -> float:  # pragma: no cover
    import resource

    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


async def _principal(  # pragma: no cover - rede e dados reais (roda no GitHub Actions)
    meses: int,
    fim: str,
    payout: float,
    treino_meses: int,
    holdout_meses: int,
    saida: Path,
    ablacao_fs1: bool,
    entrada_max_s: int | None = None,
    tolerancia_atr: float | None = None,
) -> None:
    import gc
    import time

    import httpx
    import numpy as np

    from sinais.backtest.historico import baixar_meses
    from sinais.backtest.laboratorio import _mes
    from sinais.backtest.precos import SeriePrecos
    from sinais.core.dominio import Expiracao
    from sinais.features.fs2 import combinar_fs2
    from sinais.features.microestrutura import AgregadorMicro, features_microestrutura
    from sinais.modelos.avaliacao import ResultadoCombinacao
    from sinais.modelos.avaliacao_v2 import avaliar_combinacao_v2
    from sinais.modelos.blocos import montar_snapshot_em_blocos
    from sinais.modelos.dados_1s import baixar_mes_1s
    from sinais.modelos.decisao import consolidar

    inicio_total = time.monotonic()

    def log(msg: str) -> None:
        dt = (time.monotonic() - inicio_total) / 60
        print(f"[{dt:6.1f} min | pico {_memoria_mb():6.0f} MB] {msg}", flush=True)

    periodo = meses_ate(fim, meses)
    execucao: dict[str, Any] = {
        "entrada_max_ms": None if entrada_max_s is None else entrada_max_s * 1000,
        "tolerancia_atr": tolerancia_atr,
    }
    variacoes = []
    if entrada_max_s is not None:
        variacoes.append(f"entrada sorteada entre decisão + 2 s e decisão + {entrada_max_s} s")
    if tolerancia_atr is not None:
        variacoes.append(f"tolerância de preço na entrada de {tolerancia_atr} x ATR(14) de 1m")
    diagnostico = "; ".join(variacoes) or None
    candidato: dict[tuple[str, Expiracao], ResultadoCombinacao] = {}
    sem_filtro: dict[tuple[str, Expiracao], ResultadoCombinacao] = {}
    fs1: dict[tuple[str, Expiracao], ResultadoCombinacao] = {}
    extras: dict[tuple[str, str], ExtrasFiltro] = {}
    lacunas: list[str] = []
    linhas_1s: dict[str, int] = {}
    async with httpx.AsyncClient() as http:
        for ativo in ATIVOS:
            df_1m, lac = await baixar_meses(http, ativo, "1m", periodo)
            lacunas += lac
            log(f"{ativo}: {len(df_1m)} candles de 1m; lacunas: {lac or 'nenhuma'}")
            agregador = AgregadorMicro()
            ts: list[np.ndarray] = []
            cs: list[np.ndarray] = []
            for ano, mes in periodo:
                df_1s = await baixar_mes_1s(http, ativo, ano, mes)
                if df_1s is None:
                    lacunas.append(f"{ativo} 1s {ano:04d}-{mes:02d}")
                    log(f"{ativo} {ano:04d}-{mes:02d}: 1 s ausente")
                    continue
                agregador.adicionar(df_1s)
                ts.append(df_1s.index.to_numpy(dtype="int64"))
                cs.append(df_1s["c"].to_numpy(dtype="float64"))
                log(f"{ativo} {ano:04d}-{mes:02d}: {len(df_1s)} segundos")
                del df_1s
                gc.collect()
            t = np.concatenate(ts)
            c = np.concatenate(cs)
            del ts, cs
            linhas_1s[ativo] = len(t)
            precos = SeriePrecos(t, c, c, 1000)
            micro = features_microestrutura(agregador.resultado())
            del agregador
            snap_fs1 = montar_snapshot_em_blocos(df_1m)
            colunas_fs1 = list(snap_fs1.columns)
            snap = combinar_fs2(snap_fs1, micro)
            del snap_fs1, micro
            gc.collect()
            log(f"{ativo}: snapshot fs-2 {snap.shape}")
            for exp in (Expiracao.M1, Expiracao.M5):
                r = avaliar_combinacao_v2(
                    df_1m, snap, precos, exp, payout, treino_meses=treino_meses,
                    holdout_meses=holdout_meses, **execucao,
                )  # fmt: skip
                candidato[(ativo, exp)] = r.principal
                sem_filtro[(ativo, exp)] = r.sem_filtro
                extras[(ativo, f"{int(exp) // 60}m")] = ExtrasFiltro(
                    r.limiares_filtro, r.frac_filtrada, r.limiar_filtro_holdout,
                    r.frac_filtrada_holdout,
                )  # fmt: skip
                log(f"{ativo} {exp.name}: {r.principal.dobras} dobras; {r.principal.avisos}")
                if ablacao_fs1:
                    r1 = avaliar_combinacao_v2(
                        df_1m, snap[colunas_fs1], precos, exp, payout,
                        treino_meses=treino_meses, holdout_meses=holdout_meses, **execucao,
                    )  # fmt: skip
                    fs1[(ativo, exp)] = r1.principal
                    log(f"{ativo} {exp.name} (fs-1): {r1.principal.dobras} dobras")
                gc.collect()
            del snap, precos, t, c, df_1m
            gc.collect()
    linhas = consolidar(candidato, payout)
    diagnosticos = {"fs-2 sem filtro": consolidar(sem_filtro, payout)}
    if fs1:
        diagnosticos["fs-1 + filtro, rótulos de 1 s"] = consolidar(fs1, payout)
    hipoteses = {
        "fonte": f"data.binance.vision, klines de 1m e 1s, {_mes(periodo[0])} a "
        f"{_mes(periodo[-1])} ({meses} meses; segundos por ativo: {linhas_1s})",
        "modelo": "HistGradientBoosting (hiperparâmetros da Fase 6, sem busca) + calibração "
        "isotônica; features fs-2 = fs-1 + 17 de microestrutura de 1 s + 3 de calendário",
        "rótulo": "entrada num segundo sorteado entre decisão + 2 s e o prazo de compra; "
        "vencimento alinhado ao relógio da Exnova; preço = fechamento do candle de 1 s",
        "treino da direção": "só amostras de treino não apertadas",
        "calibração": "mês de calibração dividido em duas metades purgadas (embargo de 1 h): "
        "isotônica na primeira; limiar do filtro na segunda",
        "filtro de apertados": "HGB prevê apertado (|Δ| ≤ 0,01%); limiar escolhido na 2ª metade "
        "da calibração entre sem filtro e cortar os 10%/25%/50% mais prováveis (maior Wilson "
        "inf.)",
        "execução": diagnostico
        or "padrão: entrada sorteada em toda a janela de compra, sem tolerância de preço",
        "walk-forward": f"treino {treino_meses} meses (1 a cada 3 minutos) → calibração 1 mês → "
        f"teste 1 mês; purga pelo vencimento real e embargo de 1 h; holdout final de "
        f"{holdout_meses} meses avaliado uma vez",
        "simulação": "teste, holdout e estratégias simples com 1 s e entrada sorteada (semente "
        "7); um sinal ativo por vez",
        "decisão": "COMPRA se p ≥ equilíbrio + 1 p.p.; VENDA se p ≤ 1 − (equilíbrio + 1 p.p.)",
        "payout": f"{payout} (caso de decisão: menor payout informado da Exnova)",
        "cortes": "1m: 30 s (confirmado); 5m: 100 s (hipótese de 1/3 da grade)",
        "lacunas": ", ".join(lacunas) or "nenhuma",
    }
    saida.mkdir(parents=True, exist_ok=True)
    texto = gerar_markdown_v2(linhas, diagnosticos, extras, hipoteses, diagnostico)
    texto += f"\nTempo total: {(time.monotonic() - inicio_total) / 60:.1f} min; pico de memória "
    texto += f"{_memoria_mb():.0f} MB.\n"
    (saida / "decisao_v2.md").write_text(texto, encoding="utf-8")
    (saida / "decisao_v2.json").write_text(_json(linhas, diagnosticos), encoding="utf-8")
    print(texto)


if __name__ == "__main__":  # pragma: no cover
    from sinais.backtest.laboratorio import _mes, _ultimos_meses

    p = argparse.ArgumentParser()
    p.add_argument("--meses", type=int, default=24)
    p.add_argument("--fim", default=_mes(_ultimos_meses(1)[0]), help="último mês, AAAA-MM")
    p.add_argument("--payout", type=float, default=0.86)
    p.add_argument("--treino-meses", type=int, default=6)
    p.add_argument("--holdout-meses", type=int, default=3)
    p.add_argument("--sem-ablacao-fs1", action="store_true")
    p.add_argument("--entrada-max-s", type=int, default=None, help="diagnóstico")
    p.add_argument("--tolerancia-atr", type=float, default=None, help="diagnóstico")
    p.add_argument("--saida", type=Path, default=Path("relatorio"))
    a = p.parse_args()
    asyncio.run(
        _principal(
            a.meses, a.fim, a.payout, a.treino_meses, a.holdout_meses, a.saida,
            not a.sem_ablacao_fs1, a.entrada_max_s, a.tolerancia_atr,
        )
    )  # fmt: skip
