"""Relatório do laboratório em Markdown e JSON, com as hipóteses sempre no topo."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from sinais.backtest.metricas import Metricas, benjamini_hochberg

N_MINIMO = 300
MARGEM = 0.01


@dataclass(frozen=True)
class LinhaRelatorio:
    ativo: str
    expiracao: str
    estrategia: str
    metricas: Metricas
    meses_acima: float  # fração dos meses com taxa acima do ponto de equilíbrio


def aprovacoes(linhas: Sequence[LinhaRelatorio]) -> list[bool]:
    """Critério do design §13.3 (sem a parte de superar baselines, que vale para modelos)."""
    pv = [1.0 if math.isnan(x.metricas.pvalor) else x.metricas.pvalor for x in linhas]
    bh = benjamini_hochberg(pv)
    return [
        ok
        and x.metricas.wins + x.metricas.losses >= N_MINIMO
        and x.metricas.wilson_inf > x.metricas.p_equilibrio + MARGEM
        and x.meses_acima >= 0.7
        for x, ok in zip(linhas, bh, strict=True)
    ]


def _pct(x: float) -> str:
    return "—" if math.isnan(x) else f"{100 * x:.2f}%"


def gerar_markdown(linhas: Sequence[LinhaRelatorio], hipoteses: Mapping[str, str]) -> str:
    aprov = aprovacoes(linhas)
    partes = ["# Relatório do laboratório", "", "## Hipóteses e fonte", ""]
    partes += [f"- **{k}:** {v}" for k, v in hipoteses.items()]
    partes += [
        "",
        "## Resultados",
        "",
        "| Ativo | Expiração | Estratégia | Decididas | Empates | Sem dado | Fora da janela "
        "| Apertados | Taxa | Taxa s/ apertados | Wilson inf. | Equilíbrio | Valor esperado "
        "| Meses acima | Aprovada |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for x, ok in zip(linhas, aprov, strict=True):
        m = x.metricas
        ve = "—" if math.isnan(m.valor_esperado) else f"{m.valor_esperado:+.4f}"
        partes.append(
            f"| {x.ativo} | {x.expiracao} | {x.estrategia} | {m.wins + m.losses} | {m.ties} "
            f"| {m.sem_dado} | {m.fora_janela} | {m.apertados} | {_pct(m.taxa)} "
            f"| {_pct(m.taxa_sem_apertados)} | {_pct(m.wilson_inf)} "
            f"| {_pct(m.p_equilibrio)} | {ve} "
            f"| {_pct(x.meses_acima)} | {'sim' if ok else 'não'} |"
        )
    partes += [
        "",
        f"Aprovação: Benjamini-Hochberg (q = 5%) sobre todas as linhas, pelo menos {N_MINIMO} "
        f"operações decididas, limite inferior de Wilson acima do equilíbrio + "
        f"{100 * MARGEM:.0f} p.p. e pelo menos 70% dos meses civis (com 30+ operações) acima "
        "do equilíbrio. Linhas de estratégias complementares são correlacionadas; a exigência "
        "extra de Wilson torna a correção conservadora.",
        "",
    ]
    return "\n".join(partes)


def _sem_nan(v: Any) -> Any:
    if isinstance(v, float) and not math.isfinite(v):
        return None
    if isinstance(v, dict):
        return {k: _sem_nan(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_sem_nan(x) for x in v]
    return v


def gerar_json(linhas: Sequence[LinhaRelatorio], hipoteses: Mapping[str, str]) -> str:
    aprov = aprovacoes(linhas)
    dados = {
        "hipoteses": dict(hipoteses),
        "resultados": [{**asdict(x), "aprovada": ok} for x, ok in zip(linhas, aprov, strict=True)],
    }
    return json.dumps(_sem_nan(dados), ensure_ascii=False, indent=2, allow_nan=False)
