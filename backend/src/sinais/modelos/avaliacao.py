"""Avaliação walk-forward fora da amostra de um ativo × expiração.

Em cada dobra: treina em ``treino`` (subamostrado e purgado pelo fim real do rótulo, com
embargo antes da calibração), calibra em ``calibracao`` (purgada antes do teste), decide no
``teste`` com limiar acima do equilíbrio e simula com as regras da corretora. Os últimos
``holdout_meses`` ficam de fora de tudo e são avaliados uma única vez no final.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from sinais.backtest import baselines as bl
from sinais.backtest.precos import SeriePrecos
from sinais.backtest.simulador import simular
from sinais.backtest.walk_forward import _somar_meses, dobras
from sinais.core.dominio import Expiracao
from sinais.corretoras.regras import EXNOVA, PerfilCorretora, ponto_equilibrio
from sinais.modelos.rotulos import rotular
from sinais.modelos.treino import ErroTreino, colunas_modelo, ece, treinar

_MINUTO_MS = 60_000
BASELINES: dict[str, Callable[[pd.DataFrame], pd.DataFrame]] = {
    "sempre_compra": bl.sempre_compra,
    "sempre_venda": bl.sempre_venda,
    "seguir_ultimo": bl.seguir_ultimo,
    "aleatoria": lambda df: bl.aleatoria(df, semente=42),
}


@dataclass
class ResultadoCombinacao:
    expiracao: Expiracao
    operacoes: pd.DataFrame
    holdout: pd.DataFrame
    baselines: dict[str, pd.DataFrame]
    ece_medio: float
    dobras: int
    meses_testados: int = 0
    avisos: list[str] = field(default_factory=list)


def sinais_do_modelo(decisoes: np.ndarray, p: np.ndarray, limiar: float) -> pd.DataFrame:
    direcao = np.where(p >= limiar, 1, np.where(p <= 1 - limiar, -1, 0))
    m = direcao != 0
    return pd.DataFrame({"decisao": decisoes[m], "direcao": direcao[m]}).reset_index(drop=True)


def mascara_periodo(
    rot: pd.DataFrame, inicio: int, fim: int, seguinte: int, embargo_ms: int
) -> pd.Series:
    """Decisões em ``[inicio, fim)`` com rótulo definido que termina até ``seguinte - embargo``."""
    return (
        (rot["decisao"] >= inicio)
        & (rot["decisao"] < fim)
        & rot["alvo"].notna()
        & (rot["vencimento_t"] <= seguinte - embargo_ms)
    )


def _no_periodo(rot: pd.DataFrame, inicio: int, fim: int) -> pd.Series:
    return (rot["decisao"] >= inicio) & (rot["decisao"] < fim)


def _avaliar_periodo(
    df: pd.DataFrame,
    rot: pd.DataFrame,
    x: np.ndarray,
    treino: tuple[int, int],
    calib: tuple[int, int],
    teste: tuple[int, int],
    precos: SeriePrecos,
    expiracao: Expiracao,
    perfil: PerfilCorretora,
    limiar: float,
    subamostra: int,
    embargo_ms: int,
) -> tuple[pd.DataFrame, float]:
    regra = perfil.regras[expiracao]
    m_tr = mascara_periodo(rot, *treino, calib[0], embargo_ms).to_numpy() & (
        np.arange(len(rot)) % subamostra == 0
    )
    m_ca = mascara_periodo(rot, *calib, teste[0], embargo_ms).to_numpy()
    m_te = _no_periodo(rot, *teste).to_numpy()
    y = rot["alvo"].to_numpy()
    modelo = treinar(x[m_tr], y[m_tr].astype("int64"), x[m_ca], y[m_ca].astype("int64"))
    p = modelo.probabilidade(x[m_te])
    alvo_te = y[m_te]
    definido = ~np.isnan(alvo_te)
    erro = ece(p[definido], alvo_te[definido])
    sinais = sinais_do_modelo(rot["decisao"].to_numpy()[m_te], p, limiar)
    return simular(sinais, precos, regra), erro


def avaliar_combinacao(
    df_1m: pd.DataFrame,
    snapshot: pd.DataFrame,
    expiracao: Expiracao,
    payout: float,
    perfil: PerfilCorretora = EXNOVA,
    treino_meses: int = 6,
    calibracao_meses: int = 1,
    holdout_meses: int = 3,
    subamostra: int = 3,
    embargo_ms: int = 60 * _MINUTO_MS,
    margem: float = 0.01,
) -> ResultadoCombinacao:
    if not snapshot.index.equals(df_1m.index):
        raise ValueError("snapshot e candles precisam do mesmo índice (alinhamento por posição)")
    regra = perfil.regras[expiracao]
    precos = SeriePrecos.de_quadro(df_1m, _MINUTO_MS)
    rot = rotular(df_1m, regra, precos)
    x = snapshot[colunas_modelo(snapshot)].to_numpy(dtype="float32")
    limiar = ponto_equilibrio(payout) + margem
    inicio = int(df_1m.index[0])
    fim = int(df_1m.index[-1]) + _MINUTO_MS
    ds = dobras(inicio, fim, treino_meses, calibracao_meses, 1, holdout_meses)
    avisos: list[str] = []
    partes: list[pd.DataFrame] = []
    erros: list[float] = []
    base: dict[str, list[pd.DataFrame]] = {nome: [] for nome in BASELINES}
    for d in ds:
        try:
            ops, erro = _avaliar_periodo(
                df_1m,
                rot,
                x,
                d.treino,
                d.calibracao,
                d.teste,
                precos,
                expiracao,
                perfil,
                limiar,
                subamostra,
                embargo_ms,
            )
        except ErroTreino as e:
            avisos.append(f"dobra {d.teste}: {e}")
            continue
        partes.append(ops)
        erros.append(erro)
        janela = df_1m[
            (df_1m.index >= d.teste[0] - _MINUTO_MS) & (df_1m.index < d.teste[1] - _MINUTO_MS)
        ]
        # aleatória com a mesma frequência de sinais do modelo (design §13.3)
        freq = min(1.0, len(ops) / max(1, len(janela)))
        for nome, estrategia in BASELINES.items():
            sinais_base = (
                bl.aleatoria(janela, semente=42, prob=freq)
                if nome == "aleatoria"
                else estrategia(janela)
            )
            base[nome].append(simular(sinais_base, precos, regra))
    holdout = pd.DataFrame(columns=["resultado", "entrada_t"])
    if holdout_meses:
        h_ini = _somar_meses(fim, -holdout_meses)
        h_ini = h_ini if h_ini >= inicio else inicio
        cal = (_somar_meses(h_ini, -calibracao_meses), h_ini)
        tre = (_somar_meses(cal[0], -treino_meses), cal[0])
        if tre[0] >= inicio:
            try:
                holdout, _ = _avaliar_periodo(
                    df_1m,
                    rot,
                    x,
                    tre,
                    cal,
                    (h_ini, fim),
                    precos,
                    expiracao,
                    perfil,
                    limiar,
                    subamostra,
                    embargo_ms,
                )
            except ErroTreino as e:
                avisos.append(f"holdout: {e}")
    vazio = pd.DataFrame(columns=["resultado", "entrada_t"])
    return ResultadoCombinacao(
        expiracao=expiracao,
        operacoes=pd.concat(partes, ignore_index=True) if partes else vazio,
        holdout=holdout,
        baselines={k: pd.concat(v, ignore_index=True) if v else vazio for k, v in base.items()},
        ece_medio=float(np.mean(erros)) if erros else float("nan"),
        dobras=len(partes),
        meses_testados=len(ds),
        avisos=avisos,
    )
