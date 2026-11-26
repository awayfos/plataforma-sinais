"""Avaliação das situações (pré-registro §5): critérios §13.3 por chave, família BH e "B supera A".

Chave = variação × espelho × ativo × expiração × camada (A = regra pura; B = regra + IA). As
operações chegam já simuladas (``simulacao``), com um sinal ativo por vencimento.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace

import pandas as pd
from scipy.stats import norm

from sinais.backtest import baselines as bl
from sinais.backtest.metricas import Metricas, benjamini_hochberg, calcular
from sinais.backtest.precos import SeriePrecos
from sinais.corretoras.regras import RegraVencimento, ponto_equilibrio
from sinais.situacoes.parametros import (
    ALFA_B_SUPERA_A,
    EXECUCAO,
    FRACAO_MESES,
    MARGEM_WILSON,
    MINIMO_OPS_MES,
    N_MINIMO,
    N_MINIMO_HOLDOUT,
    Q_BH,
    Execucao,
)
from sinais.situacoes.simulacao import simular_eventos

Janela = tuple[int, int]
CANDIDATA = "candidata"
NAO_VALIDADA = "histórico — não validado"


@dataclass
class LinhaSituacao:
    ativo: str
    variacao: str
    espelho: str
    expiracao: str
    camada: str
    elegivel: bool
    teste: Metricas
    holdout: Metricas
    melhor_baseline: float
    meses_acima: float
    pvalor: float
    p_b_supera_a: float = math.nan
    passou_bh: bool = False
    recomendacao: str = NAO_VALIDADA
    motivos: list[str] = field(default_factory=list)
    meses_taxas: list[float] = field(default_factory=list)


def _decididas(ops: pd.DataFrame) -> pd.DataFrame:
    return ops[ops["resultado"].isin(["WIN", "LOSS"])]


def taxas_mensais(ops: pd.DataFrame, meses: Sequence[Janela]) -> list[tuple[int, float]]:
    dec = _decididas(ops)
    d = dec["decisao"].to_numpy(dtype="int64")
    w = (dec["resultado"] == "WIN").to_numpy()
    saida = []
    for ini, fim in meses:
        m = (d >= ini) & (d < fim)
        n = int(m.sum())
        saida.append((n, float(w[m].mean()) if n else math.nan))
    return saida


def meses_acima(
    ops: pd.DataFrame, p_eq: float, meses: Sequence[Janela], minimo: int = MINIMO_OPS_MES
) -> float:
    """Fração dos meses com ≥ ``minimo`` operações decididas e taxa > ``p_eq``."""
    if not meses:
        return math.nan
    acima = sum(1 for n, t in taxas_mensais(ops, meses) if n >= minimo and t > p_eq)
    return acima / len(meses)


def p_duas_proporcoes(wb: int, nb: int, wa: int, na: int) -> float:
    """p-valor unilateral de H1: taxa B > taxa A (z com proporção combinada)."""
    if nb == 0 or na == 0:
        return 1.0
    pc = (wb + wa) / (nb + na)
    ep = math.sqrt(pc * (1 - pc) * (1 / nb + 1 / na))
    if ep == 0:
        return 1.0
    return float(norm.sf((wb / nb - wa / na) / ep))


def simular_baselines(
    janela_1m: pd.DataFrame,
    precos_1s: SeriePrecos,
    regra: RegraVencimento,
    atr_por_decisao: pd.Series,
    frequencias: Mapping[str, float],
    execucao: Execucao = EXECUCAO,
) -> dict[str, pd.DataFrame]:
    """Estratégias simples (§13.3) com a mesma execução das situações. ``frequencias``: nome →
    probabilidade de sinal da aleatória (uma por frequência de chave)."""
    saida = {
        "sempre_compra": bl.sempre_compra(janela_1m),
        "sempre_venda": bl.sempre_venda(janela_1m),
        "seguir_ultimo": bl.seguir_ultimo(janela_1m),
    }
    for nome, f in frequencias.items():
        saida[nome] = bl.aleatoria(janela_1m, semente=42, prob=min(1.0, f))
    return {
        k: simular_eventos(s, precos_1s, regra, atr_por_decisao, execucao) for k, s in saida.items()
    }


def avaliar_chave(
    *,
    ativo: str,
    variacao: str,
    espelho: str,
    expiracao: str,
    camada: str,
    elegivel: bool,
    ops_teste: pd.DataFrame,
    ops_holdout: pd.DataFrame,
    baselines: Mapping[str, pd.DataFrame],
    meses: Sequence[Janela],
    payout: float,
    ops_a: pd.DataFrame | None = None,
) -> LinhaSituacao:
    """Métricas de uma chave (sem BH, que depende da família: ``consolidar_familia``)."""
    p_eq = ponto_equilibrio(payout)
    m = calcular(ops_teste, payout)
    h = calcular(ops_holdout, payout)
    bases = [calcular(o, payout).taxa for o in baselines.values()]
    melhor = max((b for b in bases if not math.isnan(b)), default=math.nan)
    p_ba = math.nan
    if camada == "B" and ops_a is not None:
        a = calcular(ops_a, payout)
        p_ba = p_duas_proporcoes(m.wins, m.wins + m.losses, a.wins, a.wins + a.losses)
    pv = m.pvalor if elegivel and not math.isnan(m.pvalor) else 1.0
    return LinhaSituacao(
        ativo=ativo,
        variacao=variacao,
        espelho=espelho,
        expiracao=expiracao,
        camada=camada,
        elegivel=elegivel,
        teste=m,
        holdout=h,
        melhor_baseline=melhor,
        meses_acima=meses_acima(ops_teste, p_eq, meses),
        pvalor=pv,
        p_b_supera_a=p_ba,
        meses_taxas=[t for _, t in taxas_mensais(ops_teste, meses)],
    )


def consolidar_familia(linhas: Sequence[LinhaSituacao], q: float = Q_BH) -> list[LinhaSituacao]:
    """Benjamini-Hochberg sobre a família inteira e motivo de cada reprovação."""
    bh = benjamini_hochberg([x.pvalor for x in linhas], q) if linhas else []
    saida = []
    for x, passou in zip(linhas, bh, strict=True):
        m, h = x.teste, x.holdout
        p_eq = m.p_equilibrio
        motivos = []
        if not x.elegivel:
            motivos.append(
                f"fora da avaliação confirmatória (contagem < {N_MINIMO} nos meses de teste)"
            )
        if m.wins + m.losses < N_MINIMO:
            motivos.append(f"só {m.wins + m.losses} operações decididas (mínimo {N_MINIMO})")
        if not (m.wilson_inf > p_eq + MARGEM_WILSON):
            motivos.append("Wilson inferior não supera o equilíbrio + 1 p.p.")
        if not (m.taxa > x.melhor_baseline):
            motivos.append("não supera as estratégias simples")
        if not (x.meses_acima >= FRACAO_MESES):
            motivos.append(
                f"menos de 70% dos meses com ≥ {MINIMO_OPS_MES} operações acima do equilíbrio"
            )
        if not passou:
            motivos.append("não sobrevive a Benjamini-Hochberg")
        if h.wins + h.losses < N_MINIMO_HOLDOUT or not (h.taxa > p_eq):
            motivos.append(
                f"holdout sem confirmação (≥ {N_MINIMO_HOLDOUT} operações e taxa > equilíbrio)"
            )
        if x.camada == "B" and not (x.p_b_supera_a < ALFA_B_SUPERA_A):
            motivos.append("não supera a camada A (duas proporções, p < 0,05)")
        saida.append(
            replace(
                x,
                passou_bh=bool(passou),
                motivos=motivos,
                recomendacao=CANDIDATA if not motivos else NAO_VALIDADA,
            )
        )
    return saida
