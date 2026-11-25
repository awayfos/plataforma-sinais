"""Avaliação walk-forward do modelo v2 (Fase 6b): rótulos e simulação com preços de 1 s.

Mesmo esquema da Fase 6 (``avaliacao.py``): treino de ``treino_meses`` (1 a cada
``subamostra`` minutos) → calibração → teste mensal, purga pelo vencimento real com embargo e
holdout final avaliado uma vez. Diferenças, todas fixadas antes de ver resultados:

- rótulo com entrada num segundo sorteado na janela de compra (``rotular_1s``);
- o modelo de direção treina só com amostras de treino **não apertadas**; a calibração
  isotônica usa todas as amostras da calibração;
- um filtro prevê operações apertadas; o limiar sai da calibração (``escolher_limiar_filtro``);
- teste, holdout e baselines são simulados com 1 s e entrada sorteada (como um usuário real).

``sem_filtro`` é diagnóstico (mesmo modelo de direção, sem filtro); não concorre à aprovação.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from sinais.backtest import baselines as bl
from sinais.backtest.precos import SeriePrecos
from sinais.backtest.simulador import simular
from sinais.backtest.walk_forward import _somar_meses, dobras
from sinais.core.dominio import Expiracao
from sinais.corretoras.regras import EXNOVA, PerfilCorretora, RegraVencimento, ponto_equilibrio
from sinais.modelos.avaliacao import (
    BASELINES,
    ResultadoCombinacao,
    mascara_periodo,
    sinais_do_modelo,
)
from sinais.modelos.filtro import escolher_limiar_filtro, treinar_filtro
from sinais.modelos.rotulos import rotular_1s
from sinais.modelos.treino import ErroTreino, colunas_modelo, ece, treinar

_MINUTO_MS = 60_000
SEMENTE_SIMULACAO = 7


@dataclass
class ResultadoV2:
    principal: ResultadoCombinacao  # fs-x + filtro: o candidato à aprovação
    sem_filtro: ResultadoCombinacao  # diagnóstico
    limiares_filtro: list[float] = field(default_factory=list)  # por dobra (+ holdout)
    frac_filtrada: list[float] = field(default_factory=list)  # sinais cortados no teste


@dataclass
class _Periodo:
    com_filtro: pd.DataFrame
    sem_filtro: pd.DataFrame
    sinais_com: pd.DataFrame
    sinais_sem: pd.DataFrame
    erro: float
    limiar_filtro: float
    frac_filtrada: float


def _simular_1s(sinais: pd.DataFrame, precos: SeriePrecos, regra: RegraVencimento) -> pd.DataFrame:
    return simular(sinais, precos, regra, entrada_aleatoria=True, semente=SEMENTE_SIMULACAO)


def _avaliar_periodo(
    rot: pd.DataFrame,
    x: np.ndarray,
    treino: tuple[int, int],
    calib: tuple[int, int],
    teste: tuple[int, int],
    precos: SeriePrecos,
    regra: RegraVencimento,
    limiar: float,
    subamostra: int,
    embargo_ms: int,
) -> _Periodo:
    decisao = rot["decisao"].to_numpy()
    sub = np.arange(len(rot)) % subamostra == 0
    ap = rot["apertado"].to_numpy()
    m_tr = mascara_periodo(rot, *treino, calib[0], embargo_ms).to_numpy() & sub
    m_dir = m_tr & (ap == 0)
    m_fil = (
        (decisao >= treino[0])
        & (decisao < treino[1])
        & ~np.isnan(ap)
        & (rot["vencimento_t"].to_numpy() <= calib[0] - embargo_ms)
        & sub
    )
    m_ca = mascara_periodo(rot, *calib, teste[0], embargo_ms).to_numpy()
    m_te = (decisao >= teste[0]) & (decisao < teste[1])
    y = rot["alvo"].to_numpy()
    modelo = treinar(x[m_dir], y[m_dir].astype("int64"), x[m_ca], y[m_ca].astype("int64"))
    filtro = treinar_filtro(x[m_fil], ap[m_fil])
    limiar_filtro = escolher_limiar_filtro(
        modelo.probabilidade(x[m_ca]), filtro.probabilidade(x[m_ca]), y[m_ca], limiar
    )
    p = modelo.probabilidade(x[m_te])
    passa = filtro.probabilidade(x[m_te]) <= limiar_filtro
    alvo_te = y[m_te]
    definido = ~np.isnan(alvo_te)
    sinais_sem = sinais_do_modelo(decisao[m_te], p, limiar)
    sinais_com = sinais_do_modelo(decisao[m_te][passa], p[passa], limiar)
    frac = 1.0 - len(sinais_com) / len(sinais_sem) if len(sinais_sem) else 0.0
    return _Periodo(
        com_filtro=_simular_1s(sinais_com, precos, regra),
        sem_filtro=_simular_1s(sinais_sem, precos, regra),
        sinais_com=sinais_com,
        sinais_sem=sinais_sem,
        erro=ece(p[definido], alvo_te[definido]),
        limiar_filtro=limiar_filtro,
        frac_filtrada=frac,
    )


def avaliar_combinacao_v2(
    df_1m: pd.DataFrame,
    snapshot: pd.DataFrame,
    precos_1s: SeriePrecos,
    expiracao: Expiracao,
    payout: float,
    perfil: PerfilCorretora = EXNOVA,
    treino_meses: int = 6,
    calibracao_meses: int = 1,
    holdout_meses: int = 3,
    subamostra: int = 3,
    embargo_ms: int = 60 * _MINUTO_MS,
    margem: float = 0.01,
    semente_rotulo: int = 0,
) -> ResultadoV2:
    if not snapshot.index.equals(df_1m.index):
        raise ValueError("snapshot e candles precisam do mesmo índice (alinhamento por posição)")
    regra = perfil.regras[expiracao]
    decisoes = df_1m.index.to_numpy(dtype="int64") + _MINUTO_MS
    rot = rotular_1s(decisoes, regra, precos_1s, semente=semente_rotulo)
    x = snapshot[colunas_modelo(snapshot)].to_numpy(dtype="float32")
    limiar = ponto_equilibrio(payout) + margem
    inicio = int(df_1m.index[0])
    fim = int(df_1m.index[-1]) + _MINUTO_MS
    ds = dobras(inicio, fim, treino_meses, calibracao_meses, 1, holdout_meses)
    avisos: list[str] = []
    com: list[pd.DataFrame] = []
    sem: list[pd.DataFrame] = []
    erros: list[float] = []
    limiares: list[float] = []
    fracs: list[float] = []
    base: dict[str, list[pd.DataFrame]] = {nome: [] for nome in BASELINES}
    for d in ds:
        try:
            r = _avaliar_periodo(
                rot, x, d.treino, d.calibracao, d.teste, precos_1s, regra, limiar, subamostra,
                embargo_ms,
            )  # fmt: skip
        except ErroTreino as e:
            avisos.append(f"dobra {d.teste}: {e}")
            continue
        com.append(r.com_filtro)
        sem.append(r.sem_filtro)
        erros.append(r.erro)
        limiares.append(r.limiar_filtro)
        fracs.append(r.frac_filtrada)
        janela = df_1m[
            (df_1m.index >= d.teste[0] - _MINUTO_MS) & (df_1m.index < d.teste[1] - _MINUTO_MS)
        ]
        freq = min(1.0, len(r.com_filtro) / max(1, len(janela)))
        for nome, estrategia in BASELINES.items():
            sinais_base = (
                bl.aleatoria(janela, semente=42, prob=freq)
                if nome == "aleatoria"
                else estrategia(janela)
            )
            base[nome].append(_simular_1s(sinais_base, precos_1s, regra))
    vazio = pd.DataFrame(columns=["resultado", "entrada_t"])
    sinais_vazio = pd.DataFrame(columns=["decisao", "direcao"])
    h_com, h_sem, s_com, s_sem = vazio, vazio, sinais_vazio, sinais_vazio
    if holdout_meses:
        h_ini = max(_somar_meses(fim, -holdout_meses), inicio)
        cal = (_somar_meses(h_ini, -calibracao_meses), h_ini)
        tre = (_somar_meses(cal[0], -treino_meses), cal[0])
        if tre[0] >= inicio:
            try:
                h = _avaliar_periodo(
                    rot, x, tre, cal, (h_ini, fim), precos_1s, regra, limiar, subamostra,
                    embargo_ms,
                )  # fmt: skip
                h_com, h_sem, s_com, s_sem = h.com_filtro, h.sem_filtro, h.sinais_com, h.sinais_sem
                limiares.append(h.limiar_filtro)
                fracs.append(h.frac_filtrada)
            except ErroTreino as e:
                avisos.append(f"holdout: {e}")
    baselines = {k: pd.concat(v, ignore_index=True) if v else vazio for k, v in base.items()}
    comum = {
        "expiracao": expiracao,
        "baselines": baselines,
        "ece_medio": float(np.mean(erros)) if erros else math.nan,
        "dobras": len(com),
        "meses_testados": len(ds),
        "avisos": avisos,
    }
    return ResultadoV2(
        principal=ResultadoCombinacao(
            operacoes=pd.concat(com, ignore_index=True) if com else vazio,
            holdout=h_com,
            sinais_holdout=s_com,
            **comum,  # type: ignore[arg-type]
        ),
        sem_filtro=ResultadoCombinacao(
            operacoes=pd.concat(sem, ignore_index=True) if sem else vazio,
            holdout=h_sem,
            sinais_holdout=s_sem,
            **comum,  # type: ignore[arg-type]
        ),
        limiares_filtro=limiares,
        frac_filtrada=fracs,
    )
