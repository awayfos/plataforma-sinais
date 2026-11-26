"""Avaliação walk-forward do modelo v2 (Fase 6b): rótulos e simulação com preços de 1 s.

Mesmo esquema da Fase 6 (``avaliacao.py``): treino de ``treino_meses`` (1 a cada
``subamostra`` minutos) → calibração → teste mensal, purga pelo vencimento real com embargo e
holdout final avaliado uma vez. Diferenças, todas fixadas antes de ver resultados:

- rótulo com entrada num segundo sorteado na janela de compra (``rotular_1s``);
- o modelo de direção treina só com amostras de treino **não apertadas**;
- um filtro prevê operações apertadas;
- o mês de calibração é dividido em duas metades purgadas (``dividir_calibracao``): a
  calibração isotônica usa a primeira e a escolha do limiar do filtro, a segunda, para que o
  limiar não seja escolhido sobre as mesmas amostras em que a isotônica foi ajustada;
- teste, holdout e baselines são simulados com 1 s e entrada sorteada (como um usuário real).

Opcionais (padrão desligado), para o diagnóstico de sensibilidade pré-registrado: entrada
limitada a ``decisao + entrada_max_ms`` (rótulos e simulação) e tolerância de preço de
``tolerancia_atr`` x ATR(14) de 1m na entrada (design §12.6), aplicada a modelo e baselines.

``sem_filtro`` é diagnóstico (mesmo modelo de direção, sem filtro); não concorre à aprovação.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from sinais.analise.indicadores import atr as calcular_atr
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
    limiares_filtro: list[float] = field(default_factory=list)  # por dobra de teste
    frac_filtrada: list[float] = field(default_factory=list)  # sinais cortados, por dobra
    limiar_filtro_holdout: float = math.nan
    frac_filtrada_holdout: float = math.nan


@dataclass
class _Periodo:
    com_filtro: pd.DataFrame
    sem_filtro: pd.DataFrame
    sinais_com: pd.DataFrame
    sinais_sem: pd.DataFrame
    erro: float
    limiar_filtro: float
    frac_filtrada: float


@dataclass(frozen=True)
class _Execucao:
    """Como o usuário simulado entra: com 1 s, entrada sorteada, opções do diagnóstico."""

    precos: SeriePrecos
    regra: RegraVencimento
    atr_por_decisao: pd.Series | None
    entrada_max_ms: int | None
    tolerancia_atr: float | None

    def simular(self, sinais: pd.DataFrame) -> pd.DataFrame:
        if self.tolerancia_atr is not None and self.atr_por_decisao is not None:
            atr = self.atr_por_decisao.reindex(sinais["decisao"].to_numpy()).to_numpy()
            sinais = sinais.assign(atr=atr)
        return simular(
            sinais,
            self.precos,
            self.regra,
            entrada_aleatoria=True,
            semente=SEMENTE_SIMULACAO,
            entrada_max_ms=self.entrada_max_ms,
            tolerancia_atr=self.tolerancia_atr,
        )


def dividir_calibracao(
    rot: pd.DataFrame, calib: tuple[int, int], seguinte: int, embargo_ms: int
) -> tuple[np.ndarray, np.ndarray]:
    """Metades do mês de calibração: a primeira (isotônica) purgada antes da segunda; a segunda
    (limiar do filtro) purgada antes de ``seguinte`` (o teste)."""
    meio = calib[0] + (calib[1] - calib[0]) // 2
    meio -= meio % _MINUTO_MS
    m_iso = mascara_periodo(rot, calib[0], meio, meio, embargo_ms).to_numpy()
    m_lim = mascara_periodo(rot, meio, calib[1], seguinte, embargo_ms).to_numpy()
    return m_iso, m_lim


def _avaliar_periodo(
    rot: pd.DataFrame,
    x: np.ndarray,
    treino: tuple[int, int],
    calib: tuple[int, int],
    teste: tuple[int, int],
    execucao: _Execucao,
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
    m_iso, m_lim = dividir_calibracao(rot, calib, teste[0], embargo_ms)
    m_te = (decisao >= teste[0]) & (decisao < teste[1])
    y = rot["alvo"].to_numpy()
    modelo = treinar(x[m_dir], y[m_dir].astype("int64"), x[m_iso], y[m_iso].astype("int64"))
    filtro = treinar_filtro(x[m_fil], ap[m_fil])
    limiar_filtro = escolher_limiar_filtro(
        modelo.probabilidade(x[m_lim]), filtro.probabilidade(x[m_lim]), y[m_lim], limiar
    )
    p = modelo.probabilidade(x[m_te])
    passa = filtro.probabilidade(x[m_te]) <= limiar_filtro
    alvo_te = y[m_te]
    definido = ~np.isnan(alvo_te)
    sinais_sem = sinais_do_modelo(decisao[m_te], p, limiar)
    sinais_com = sinais_do_modelo(decisao[m_te][passa], p[passa], limiar)
    frac = 1.0 - len(sinais_com) / len(sinais_sem) if len(sinais_sem) else 0.0
    return _Periodo(
        com_filtro=execucao.simular(sinais_com),
        sem_filtro=execucao.simular(sinais_sem),
        sinais_com=sinais_com,
        sinais_sem=sinais_sem,
        erro=ece(p[definido], alvo_te[definido]),
        limiar_filtro=limiar_filtro,
        frac_filtrada=frac,
    )


def _baselines(
    janela: pd.DataFrame, ops_modelo: pd.DataFrame, execucao: _Execucao
) -> dict[str, pd.DataFrame]:
    # aleatória com a mesma frequência de sinais da variante avaliada (design §13.3)
    freq = min(1.0, len(ops_modelo) / max(1, len(janela)))
    saida = {}
    for nome, estrategia in BASELINES.items():
        sinais = (
            bl.aleatoria(janela, semente=42, prob=freq)
            if nome == "aleatoria"
            else estrategia(janela)
        )
        saida[nome] = execucao.simular(sinais)
    return saida


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
    entrada_max_ms: int | None = None,
    tolerancia_atr: float | None = None,
) -> ResultadoV2:
    if not snapshot.index.equals(df_1m.index):
        raise ValueError("snapshot e candles precisam do mesmo índice (alinhamento por posição)")
    regra = perfil.regras[expiracao]
    decisoes = df_1m.index.to_numpy(dtype="int64") + _MINUTO_MS
    rot = rotular_1s(
        decisoes, regra, precos_1s, semente=semente_rotulo, entrada_max_ms=entrada_max_ms
    )
    atr_por_decisao = None
    if tolerancia_atr is not None:
        atr_por_decisao = pd.Series(calcular_atr(df_1m).to_numpy(dtype="float64"), index=decisoes)
    execucao = _Execucao(precos_1s, regra, atr_por_decisao, entrada_max_ms, tolerancia_atr)
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
    base_com: dict[str, list[pd.DataFrame]] = {nome: [] for nome in BASELINES}
    base_sem: dict[str, list[pd.DataFrame]] = {nome: [] for nome in BASELINES}
    for d in ds:
        try:
            r = _avaliar_periodo(
                rot, x, d.treino, d.calibracao, d.teste, execucao, limiar, subamostra, embargo_ms
            )
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
        b_com = _baselines(janela, r.com_filtro, execucao)
        b_sem = _baselines(janela, r.sem_filtro, execucao)
        for nome in BASELINES:
            base_com[nome].append(b_com[nome])
            base_sem[nome].append(b_sem[nome])
    vazio = pd.DataFrame(columns=["resultado", "entrada_t"])
    sinais_vazio = pd.DataFrame(columns=["decisao", "direcao"])
    h_com, h_sem, s_com, s_sem = vazio, vazio, sinais_vazio, sinais_vazio
    limiar_h, frac_h = math.nan, math.nan
    if holdout_meses:
        h_ini = max(_somar_meses(fim, -holdout_meses), inicio)
        cal = (_somar_meses(h_ini, -calibracao_meses), h_ini)
        tre = (_somar_meses(cal[0], -treino_meses), cal[0])
        if tre[0] >= inicio:
            try:
                h = _avaliar_periodo(
                    rot, x, tre, cal, (h_ini, fim), execucao, limiar, subamostra, embargo_ms
                )
                h_com, h_sem, s_com, s_sem = h.com_filtro, h.sem_filtro, h.sinais_com, h.sinais_sem
                limiar_h, frac_h = h.limiar_filtro, h.frac_filtrada
            except ErroTreino as e:
                avisos.append(f"holdout: {e}")

    def juntar(partes: list[pd.DataFrame]) -> pd.DataFrame:
        return pd.concat(partes, ignore_index=True) if partes else vazio.copy()

    def resultado(
        ops: list[pd.DataFrame],
        base: dict[str, list[pd.DataFrame]],
        holdout: pd.DataFrame,
        sinais_holdout: pd.DataFrame,
    ) -> ResultadoCombinacao:
        return ResultadoCombinacao(
            expiracao=expiracao,
            operacoes=juntar(ops),
            holdout=holdout,
            baselines={k: juntar(v) for k, v in base.items()},
            ece_medio=float(np.mean(erros)) if erros else math.nan,
            dobras=len(com),
            meses_testados=len(ds),
            avisos=list(avisos),
            sinais_holdout=sinais_holdout,
        )

    return ResultadoV2(
        principal=resultado(com, base_com, h_com, s_com),
        sem_filtro=resultado(sem, base_sem, h_sem, s_sem),
        limiares_filtro=limiares,
        frac_filtrada=fracs,
        limiar_filtro_holdout=float(limiar_h),
        frac_filtrada_holdout=float(frac_h),
    )
