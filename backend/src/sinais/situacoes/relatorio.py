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
import math
import time
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sinais.core.dominio import Expiracao
from sinais.corretoras.regras import EXNOVA, RegraVencimento
from sinais.situacoes.periodos import Periodos, periodos_descoberta

if TYPE_CHECKING:
    from sinais.situacoes.avaliacao_real import ResultadoAvaliacao

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


def _pct(x: float) -> str:
    return "—" if math.isnan(x) else f"{100 * x:.2f}%"


def _p(x: float) -> str:
    return "—" if math.isnan(x) else f"{x:.2g}"


def markdown_resultado(r: ResultadoAvaliacao, hipoteses: Mapping[str, str]) -> str:
    """Relatório da descoberta: uma linha por chave (camadas A e B), conclusão e diagnósticos."""
    partes = ["# Motor de Situações — resultado da descoberta", "", "## Hipóteses e fonte", ""]
    partes += [f"- **{k}:** {v}" for k, v in hipoteses.items()]
    partes += [
        "",
        "## Resultado por chave (meses de teste agregados; holdout à parte)",
        "",
        "| Ativo | Variação | Espelho | Exp. | Camada | Elegível | n | Taxa | Wilson inf. "
        "| Melhor simples | Meses acima | Holdout n | Holdout taxa | p | BH | p (B > A) "
        "| Recomendação | Motivos |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    ordem = {"15m": 0, "5m": 1, "30m": 2}
    linhas = sorted(
        r.linhas,
        key=lambda x: (ordem.get(x.expiracao, 9), x.variacao, x.ativo, x.espelho, x.camada),
    )
    for x in linhas:
        m, h = x.teste, x.holdout
        partes.append(
            f"| {x.ativo} | {x.variacao} | {x.espelho} | {x.expiracao} | {x.camada} "
            f"| {'sim' if x.elegivel else 'não'} | {m.wins + m.losses} | {_pct(m.taxa)} "
            f"| {_pct(m.wilson_inf)} | {_pct(x.melhor_baseline)} | {_pct(x.meses_acima)} "
            f"| {h.wins + h.losses} | {_pct(h.taxa)} | {_p(x.pvalor)} "
            f"| {'sim' if x.passou_bh else 'não'} "
            f"| {_p(x.p_b_supera_a)} | **{x.recomendacao}** | {'; '.join(x.motivos) or '—'} |"
        )
    cand = [x for x in r.linhas if x.recomendacao == "candidata"]
    partes += [
        "",
        "## Camada B (tentativas)",
        "",
        "| Variação | Exp. | Tentada | Linhas de treino (mín. por dobra) | ECE médio "
        "| Limiares (teste) | Limiar holdout |",
        "|---|---|---|---|---|---|---|",
    ]
    for (var, exp), b in sorted(r.b.items()):
        if b is None:
            partes.append(
                f"| {var} | {exp} | não (< 1.000 linhas em alguma dobra) | — | — | — | — |"
            )
        else:
            lims = ", ".join("—" if math.isnan(v) else f"{v:.3f}" for v in b.limiares)
            partes.append(
                f"| {var} | {exp} | sim | {b.linhas_treino_min} | {_pct(b.ece_medio)} | {lims} "
                f"| {b.limiar_holdout:.3f} |"
            )
    if not r.diagnostico_toques.empty:
        partes += [
            "",
            "## Diagnóstico: taxa por ordem do toque (15m, camada A, sem direito a aprovação)",
            "",
            "| Ativo | Variação | Espelho | Toque | n | Taxa |",
            "|---|---|---|---|---|---|",
        ]
        for x in r.diagnostico_toques.itertuples(index=False):
            partes.append(
                f"| {x.ativo} | {x.variacao} | {x.espelho} | {x.toque} | {x.n} "
                f"| {_pct(float(x.taxa))} |"
            )
    partes += ["", "## Conclusão", ""]
    if cand:
        nomes = ", ".join(
            f"{x.variacao} {x.espelho} {x.ativo} {x.expiracao} ({x.camada})" for x in cand
        )
        partes.append(
            f"Chaves **candidatas** (passaram em todos os critérios da descoberta): {nomes}. "
            "Nenhuma é liberada como sinal antes da confirmação em meses novos (≥ 2026-11)."
        )
    else:
        partes.append(
            "Nenhuma chave passou em todos os critérios da descoberta. Todas as situações ficam "
            "como "
            '"Histórico — não validado" e nenhum botão COMPRA/VENDA é liberado.'
        )
    return "\n".join(partes) + "\n"


def candidatas_json(r: ResultadoAvaliacao) -> list[dict[str, Any]]:
    return [
        {"ativo": x.ativo, "variacao": x.variacao, "espelho": x.espelho, "expiracao": x.expiracao,
         "camada": x.camada}
        for x in r.linhas
        if x.recomendacao == "candidata"
    ]  # fmt: skip


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


def _memoria_mb() -> float:  # pragma: no cover
    import resource

    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


async def carregar_ativo(  # pragma: no cover - rede
    http: Any, ativo: str, p: Periodos, log: Any
) -> tuple[Any, Any, Any, list[str]]:
    """1m do período, preços de 1 s (só tempo e fechamento) e microestrutura agregada mês a mês."""
    import gc

    import numpy as np

    from sinais.backtest.historico import baixar_meses
    from sinais.backtest.precos import SeriePrecos
    from sinais.features.microestrutura import AgregadorMicro, features_microestrutura
    from sinais.modelos.dados_1s import baixar_mes_1s

    df_1m, lacunas = await baixar_meses(http, ativo, "1m", _meses(p))
    log(f"{ativo}: {len(df_1m)} candles de 1m; lacunas: {lacunas or 'nenhuma'}")
    agregador = AgregadorMicro()
    ts, cs = [], []
    for ano, mes in _meses(p):
        df_1s = await baixar_mes_1s(http, ativo, ano, mes)
        if df_1s is None:
            lacunas.append(f"{ativo} 1s {ano:04d}-{mes:02d}")
            continue
        agregador.adicionar(df_1s)
        ts.append(df_1s.index.to_numpy(dtype="int64"))
        cs.append(df_1s["c"].to_numpy(dtype="float64"))
        del df_1s
        gc.collect()
    t, c = np.concatenate(ts), np.concatenate(cs)
    del ts, cs
    log(f"{ativo}: {len(t)} segundos")
    micro = features_microestrutura(agregador.resultado())
    return df_1m, SeriePrecos(t, c, c, 1000), micro, lacunas


async def _avaliacao(  # pragma: no cover - rede
    ativos: list[str], fim: str, meses: int, payout: float, saida: Path
) -> None:
    import gc
    import json

    import httpx

    from sinais.situacoes.avaliacao_real import avaliar, processar_ativo

    inicio = time.monotonic()

    def log(msg: str) -> None:
        dt = (time.monotonic() - inicio) / 60
        print(f"[{dt:6.1f} min | pico {_memoria_mb():6.0f} MB] {msg}", flush=True)

    p = periodos_descoberta(fim, meses)
    processados = []
    lacunas: list[str] = []
    async with httpx.AsyncClient() as http:
        for ativo in ativos:
            df_1m, precos, micro, lac = await carregar_ativo(http, ativo, p, log)
            lacunas += lac
            processados.append(processar_ativo(ativo, df_1m, precos, micro, p, REGRAS))
            log(f"{ativo}: processado ({len(processados[-1].eventos)} eventos sem conflito)")
            del df_1m, precos, micro
            gc.collect()
    r = avaliar(processados, p, REGRAS, payout)
    log("avaliação concluída")
    meses_txt = _meses(p)
    hipoteses = {
        "pré-registro": "docs/laboratorio/2026-11-26-situacoes-pre-registro.md (commit fb8bc3a)",
        "fonte": f"data.binance.vision, klines de 1m e 1 s, {meses_txt[0]} a {meses_txt[-1]}; "
        f"ativos {', '.join(ativos)}; lacunas: {', '.join(lacunas) or 'nenhuma'}",
        "execução": "entrada em decisão + 2..10 s (hash do instante, semente 7); recusa se o preço "
        "andou > 0,5 × ATR(14) de 1m; vencimento alinhado ao relógio da Exnova, válido só se "
        "vencimento − decisão ≤ grade; preço = fechamento do 1 s; um sinal por vencimento",
        "walk-forward": "14 meses de teste (2025-06 a 2026-07); holdout 2026-08 a 2026-10 (já "
        "visto "
        "na Fase 6, declarado); camada B: treino 6 meses, calibração 1 mês, embargo 1 h",
        "payout": f"{payout} (equilíbrio {100 / (1 + payout):.2f}%)",
        "cortes": "15m: 5 min (confirmado); 5m: 100 s e 30m: 10 min (hipóteses)",
        "conflitos": ", ".join(f"{x.ativo}: {x.conflitos}" for x in processados),
    }
    texto = markdown_resultado(r, hipoteses)
    texto += (
        f"\nTempo total: {(time.monotonic() - inicio) / 60:.1f} min; pico {_memoria_mb():.0f} MB.\n"
    )
    saida.mkdir(parents=True, exist_ok=True)
    (saida / "resultado.md").write_text(texto, encoding="utf-8")
    (saida / "candidatas.json").write_text(
        json.dumps(candidatas_json(r), indent=1), encoding="utf-8"
    )
    print(texto, flush=True)
    print("CANDIDATAS_JSON=" + json.dumps(candidatas_json(r)), flush=True)


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
        asyncio.run(_avaliacao(ativos, args.fim, args.meses, args.payout, args.saida))
