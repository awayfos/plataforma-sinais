"""Camada B — IA qualificadora (design §5 e §9b.5; pré-registro §5).

Um modelo por variação × expiração, juntando espelhos e ativos, treinado só nas linhas em que a
situação disparou. HistGradientBoosting com os hiperparâmetros da Fase 6 + calibração isotônica
por validação cruzada temporal dentro do bloco de treino; limiar escolhido no mês de calibração.
A saída diz quais eventos do teste (e do holdout) a camada B libera; a simulação com um sinal por
vencimento é aplicada depois, por chave, igual à da camada A.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import TimeSeriesSplit

from sinais.backtest.metricas import wilson
from sinais.modelos.treino import HIPERPARAMETROS, ErroTreino, ModeloCalibrado, ece
from sinais.situacoes.parametros import (
    DOBRAS_CV_B,
    EMBARGO_MS,
    LIMIARES_B,
    LINHAS_MINIMAS_B,
    MINIMO_CALIBRACAO_B,
)
from sinais.situacoes.periodos import Janela, Periodos


@dataclass
class ResultadoB:
    liberado_teste: np.ndarray  # máscara sobre as linhas de ``dados``
    liberado_holdout: np.ndarray
    limiares: list[float] = field(default_factory=list)  # por mês de teste
    limiar_holdout: float = math.nan
    ece_medio: float = math.nan
    linhas_treino_min: int = 0


@dataclass
class _ComColunas:
    """Modelo treinado só nas colunas com algum valor no treino (o HGB do scikit-learn 1.9 falha
    no binning de uma coluna inteira de NaN, ex.: ``ordem_toque`` em S1). Coluna toda vazia não
    carrega informação: tirá-la não muda o modelo."""

    colunas: np.ndarray
    modelo: ModeloCalibrado

    def probabilidade(self, x: np.ndarray) -> np.ndarray:
        return self.modelo.probabilidade(x[:, self.colunas])


def treinar_qualificadora(x: np.ndarray, y: np.ndarray) -> _ComColunas:
    """``x`` em ordem de tempo. Isotônica por ``TimeSeriesSplit`` dentro do próprio treino."""
    if len(np.unique(y)) < 2:
        raise ErroTreino("treino: só há uma classe")
    base = HistGradientBoostingClassifier(**HIPERPARAMETROS)
    cv = TimeSeriesSplit(n_splits=DOBRAS_CV_B)
    # o treino de cada parte da validação cruzada é um prefixo: basta olhar o menor
    menor = next(iter(cv.split(x)))[0]
    colunas = np.flatnonzero(~np.isnan(x[menor]).all(axis=0))
    x = x[:, colunas]
    for tr, _ in cv.split(x):
        if len(np.unique(y[tr])) < 2:
            raise ErroTreino("validação cruzada temporal: parte com uma classe só")
    calibrado = CalibratedClassifierCV(base, method="isotonic", cv=cv).fit(x, y)
    return _ComColunas(colunas, ModeloCalibrado(calibrado))


def escolher_limiar(
    p: np.ndarray,
    y: np.ndarray,
    p_eq: float,
    margens: Sequence[float] = LIMIARES_B,
    minimo: int = MINIMO_CALIBRACAO_B,
) -> float:
    """Maior Wilson inferior entre os eventos com ``p ≥ p_eq + margem`` (≥ ``minimo`` decididos);
    empate fica com o limiar mais baixo; nenhum válido → ``p_eq + margens[0]``."""
    melhor, escolhido = -math.inf, p_eq + margens[0]
    for m in margens:
        sel = p >= p_eq + m
        n = int(sel.sum())
        if n < minimo:
            continue
        inf, _ = wilson(int(y[sel].sum()), n)
        if inf > melhor:
            melhor, escolhido = inf, p_eq + m
    return escolhido


def _mascaras(
    dados: pd.DataFrame, treino: Janela, calib: Janela, teste: Janela
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    d = dados["decisao"].to_numpy(dtype="int64")
    v = dados["vencimento_t"].to_numpy(dtype="int64")
    decidido = dados["resultado"].isin(["WIN", "LOSS"]).to_numpy()
    m_tr = (d >= treino[0]) & (d < treino[1]) & (v <= calib[0] - EMBARGO_MS) & decidido
    m_ca = (d >= calib[0]) & (d < calib[1]) & (v <= teste[0] - EMBARGO_MS) & decidido
    m_te = (d >= teste[0]) & (d < teste[1])
    return m_tr, m_ca, m_te


def avaliar_b(
    dados: pd.DataFrame, colunas: Sequence[str], periodos: Periodos, p_eq: float
) -> ResultadoB | None:
    """``dados``: eventos sem conflito (uma variação × expiração, todos os espelhos e ativos), em
    ordem de decisão, com ``decisao``, ``vencimento_t``, ``resultado`` (simulação um a um) e as
    ``colunas`` de variáveis. ``None`` = camada B não tentada (alguma dobra com < 1.000 linhas)."""
    if not dados["decisao"].is_monotonic_increasing:
        raise ValueError("dados precisam estar em ordem de decisão (as máscaras são posicionais)")
    janelas = [(d.treino, d.calibracao, d.teste) for d in periodos.dobras]
    janelas.append((periodos.treino_holdout, periodos.calibracao_holdout, periodos.holdout))
    mascaras = [_mascaras(dados, *j) for j in janelas]
    minimo = min(int(m[0].sum()) for m in mascaras)
    if minimo < LINHAS_MINIMAS_B:
        return None
    x = dados[list(colunas)].to_numpy(dtype="float32")
    y = (dados["resultado"] == "WIN").to_numpy().astype("int64")
    liberado = [np.zeros(len(dados), dtype="bool"), np.zeros(len(dados), dtype="bool")]
    limiares: list[float] = []
    erros: list[float] = []
    limiar_h = math.nan
    for k, (m_tr, m_ca, m_te) in enumerate(mascaras):
        holdout = k == len(mascaras) - 1
        try:
            modelo = treinar_qualificadora(x[m_tr], y[m_tr])
        except ErroTreino:
            if not holdout:
                limiares.append(math.nan)
            continue
        limiar = escolher_limiar(modelo.probabilidade(x[m_ca]), y[m_ca], p_eq)
        p_te = modelo.probabilidade(x[m_te])
        idx = np.flatnonzero(m_te)
        liberado[1 if holdout else 0][idx[p_te >= limiar]] = True
        if holdout:
            limiar_h = limiar
        else:
            limiares.append(limiar)
            dec = m_te & dados["resultado"].isin(["WIN", "LOSS"]).to_numpy()
            if dec.any():
                erros.append(ece(modelo.probabilidade(x[dec]), y[dec].astype("float64")))
    return ResultadoB(
        liberado_teste=liberado[0],
        liberado_holdout=liberado[1],
        limiares=limiares,
        limiar_holdout=limiar_h,
        ece_medio=float(np.mean(erros)) if erros else math.nan,
        linhas_treino_min=minimo,
    )
