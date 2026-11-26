"""Rodada de avaliação do motor de situações (pré-registro §5), ativo por ativo.

``processar_ativo`` faz tudo o que precisa dos segundos (simulação de cada evento uma a uma,
estratégias simples, ``fs-2`` nas linhas dos eventos) e devolve só o que é pequeno, para liberar o
1 s antes do próximo ativo. ``avaliar`` aplica a regra de um sinal por vencimento por chave
(``aplicar_sobreposicao``), treina a camada B juntando os ativos e consolida a família.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from sinais.analise.indicadores import atr
from sinais.backtest import baselines as bl
from sinais.backtest.metricas import calcular
from sinais.backtest.precos import SeriePrecos
from sinais.corretoras.regras import RegraVencimento, ponto_equilibrio
from sinais.situacoes.avaliacao import LinhaSituacao, avaliar_chave, consolidar_familia
from sinais.situacoes.contagem import tabela_contagem
from sinais.situacoes.features_b import matriz_b, snapshot_fs2_nas_linhas
from sinais.situacoes.motor import detectar_todas
from sinais.situacoes.parametros import ESPELHOS, EXECUCAO, MINUTO_MS, N_ATR, VARIACOES, Execucao
from sinais.situacoes.periodos import Janela, Periodos
from sinais.situacoes.qualificadora import ResultadoB, avaliar_b
from sinais.situacoes.simulacao import aplicar_sobreposicao, simular_eventos

_FIXAS = ("sempre_compra", "sempre_venda", "seguir_ultimo")


@dataclass
class ProcessadoAtivo:
    ativo: str
    eventos: pd.DataFrame  # sem conflito, com contexto
    ops_ind: dict[str, pd.DataFrame]  # expiração → simulação um a um (alinhada a ``eventos``)
    fixas: dict[str, dict[str, pd.DataFrame]]  # expiração → estratégia → operações no teste
    aleatoria_ind: dict[str, pd.DataFrame]  # expiração → um a um, com sorteio ``u`` por minuto
    snapshot: pd.DataFrame
    contagem: pd.DataFrame
    minutos_teste: int
    conflitos: int


@dataclass
class ResultadoAvaliacao:
    linhas: list[LinhaSituacao]
    b: dict[tuple[str, str], ResultadoB | None] = field(default_factory=dict)
    diagnostico_toques: pd.DataFrame = field(default_factory=pd.DataFrame)


def _na(janela: Janela, d: pd.Series) -> pd.Series:
    return (d >= janela[0]) & (d < janela[1])


def processar_ativo(
    ativo: str,
    df_1m: pd.DataFrame,
    precos_1s: SeriePrecos,
    micro: pd.DataFrame,
    periodos: Periodos,
    regras: Mapping[str, RegraVencimento],
    execucao: Execucao = EXECUCAO,
) -> ProcessadoAtivo:
    todos = detectar_todas(df_1m)
    eventos = todos[~todos["conflito"]].reset_index(drop=True).assign(ativo=ativo)
    decisoes = df_1m.index.to_numpy(dtype="int64") + MINUTO_MS
    atr_dec = pd.Series(atr(df_1m, N_ATR).to_numpy(dtype="float64"), index=decisoes)
    janela = df_1m[_na(periodos.teste, pd.Series(decisoes, index=df_1m.index))]
    rng = np.random.default_rng(42)  # mesmo sorteio de backtest.baselines.aleatoria
    dir_aleat = rng.choice([-1, 1], size=len(janela))
    u = rng.random(len(janela))
    ops_ind: dict[str, pd.DataFrame] = {}
    fixas: dict[str, dict[str, pd.DataFrame]] = {}
    aleatoria: dict[str, pd.DataFrame] = {}
    for exp, regra in regras.items():
        ops = simular_eventos(eventos, precos_1s, regra, atr_dec, execucao, sem_sobreposicao=False)
        ops_ind[exp] = ops  # eventos já estão em ordem de decisão (ordenação estável)
        sinais = {
            "sempre_compra": bl.sempre_compra(janela),
            "sempre_venda": bl.sempre_venda(janela),
            "seguir_ultimo": bl.seguir_ultimo(janela),
        }
        fixas[exp] = {
            k: simular_eventos(s, precos_1s, regra, atr_dec, execucao) for k, s in sinais.items()
        }
        alea = pd.DataFrame({"decisao": janela.index.to_numpy(dtype="int64") + MINUTO_MS})
        alea["direcao"] = dir_aleat
        ind = simular_eventos(alea, precos_1s, regra, atr_dec, execucao, sem_sobreposicao=False)
        aleatoria[exp] = ind.assign(u=u)
    linhas = pd.Index(eventos["decisao"].to_numpy(dtype="int64") - MINUTO_MS, dtype="int64")
    snapshot = snapshot_fs2_nas_linhas(df_1m, micro, linhas)
    per = {
        "teste": periodos.teste,
        "holdout": periodos.holdout,
        "total": (periodos.inicio, periodos.fim),
    }
    contagem = tabela_contagem(todos.assign(ativo=ativo), per, regras, [ativo])
    return ProcessadoAtivo(
        ativo=ativo,
        eventos=eventos,
        ops_ind=ops_ind,
        fixas=fixas,
        aleatoria_ind=aleatoria,
        snapshot=snapshot,
        contagem=contagem,
        minutos_teste=len(janela),
        conflitos=int(todos["conflito"].sum()),
    )


def _ops_chave(p: ProcessadoAtivo, exp: str, mascara: np.ndarray, janela: Janela) -> pd.DataFrame:
    ops = p.ops_ind[exp]
    m = mascara & _na(janela, ops["decisao"]).to_numpy()
    return aplicar_sobreposicao(ops[m])


def _baselines(p: ProcessadoAtivo, exp: str, n_eventos: int) -> dict[str, pd.DataFrame]:
    f = n_eventos / max(1, p.minutos_teste)
    ind = p.aleatoria_ind[exp]
    return {**p.fixas[exp], "aleatoria": aplicar_sobreposicao(ind[ind["u"] < f])}


def avaliar(
    processados: Sequence[ProcessadoAtivo],
    periodos: Periodos,
    regras: Mapping[str, RegraVencimento],
    payout: float,
    camada_b: bool = True,
) -> ResultadoAvaliacao:
    p_eq = ponto_equilibrio(payout)
    meses = periodos.meses_teste
    linhas: list[LinhaSituacao] = []
    resultados_b: dict[tuple[str, str], ResultadoB | None] = {}
    diag: list[dict[str, object]] = []
    for exp in regras:
        ops_a: dict[tuple[str, str, str], pd.DataFrame] = {}
        for v in VARIACOES:
            for p in processados:
                elegivel_tab = p.contagem[p.contagem["expiracao"] == exp].set_index(
                    ["variacao", "espelho"]
                )["elegivel"]
                for espelho in ESPELHOS:
                    m = (
                        (p.eventos["variacao"] == v.nome) & (p.eventos["espelho"] == espelho)
                    ).to_numpy()
                    teste = _ops_chave(p, exp, m, periodos.teste)
                    ops_a[(v.nome, espelho, p.ativo)] = teste
                    n_ev = int((m & _na(periodos.teste, p.eventos["decisao"]).to_numpy()).sum())
                    linhas.append(
                        avaliar_chave(
                            ativo=p.ativo, variacao=v.nome, espelho=espelho, expiracao=exp,
                            camada="A", elegivel=bool(elegivel_tab.get((v.nome, espelho), False)),
                            ops_teste=teste, ops_holdout=_ops_chave(p, exp, m, periodos.holdout),
                            baselines=_baselines(p, exp, n_ev), meses=meses, payout=payout,
                        )
                    )  # fmt: skip
                    if exp == "15m" and not np.isnan(p.eventos.loc[m, "ordem_toque"]).all():
                        diag += _por_toque(p, exp, m, periodos.teste, v.nome, espelho, payout)
            if not camada_b:
                continue
            r, dados = _camada_b(processados, exp, v.nome, periodos, p_eq)
            resultados_b[(v.nome, exp)] = r
            if r is None:
                continue
            for p in processados:
                elegivel_tab = p.contagem[p.contagem["expiracao"] == exp].set_index(
                    ["variacao", "espelho"]
                )["elegivel"]
                for espelho in ESPELHOS:
                    m = ((dados["ativo"] == p.ativo) & (dados["espelho"] == espelho)).to_numpy()
                    cols = list(p.ops_ind[exp].columns)
                    teste = aplicar_sobreposicao(dados.loc[m & r.liberado_teste, cols])
                    hold = aplicar_sobreposicao(dados.loc[m & r.liberado_holdout, cols])
                    n_ev = int((m & r.liberado_teste).sum())
                    linhas.append(
                        avaliar_chave(
                            ativo=p.ativo, variacao=v.nome, espelho=espelho, expiracao=exp,
                            camada="B", elegivel=bool(elegivel_tab.get((v.nome, espelho), False)),
                            ops_teste=teste, ops_holdout=hold, baselines=_baselines(p, exp, n_ev),
                            meses=meses, payout=payout, ops_a=ops_a[(v.nome, espelho, p.ativo)],
                        )
                    )  # fmt: skip
    return ResultadoAvaliacao(consolidar_familia(linhas), resultados_b, pd.DataFrame(diag))


def _camada_b(
    processados: Sequence[ProcessadoAtivo], exp: str, variacao: str, periodos: Periodos, p_eq: float
) -> tuple[ResultadoB | None, pd.DataFrame]:
    partes = []
    for p in processados:
        m = (p.eventos["variacao"] == variacao).to_numpy()
        ev = p.eventos[m]
        ops = p.ops_ind[exp][m]
        x, colunas = matriz_b(ev.assign(vencimento_t=ops["vencimento_t"].to_numpy()), p.snapshot)
        ids = ev[["ativo", "espelho", "variacao"]].reset_index(drop=True)
        juntos = [ops.reset_index(drop=True), ids, x.reset_index(drop=True)]
        partes.append(pd.concat(juntos, axis=1))
    if not partes:
        return None, pd.DataFrame()
    dados = pd.concat(partes, ignore_index=True)
    dados = dados.loc[:, ~dados.columns.duplicated()]
    dados = dados.sort_values("decisao", kind="stable").reset_index(drop=True)
    return avaliar_b(dados, colunas, periodos, p_eq), dados


def _por_toque(
    p: ProcessadoAtivo, exp: str, m: np.ndarray, janela: Janela, var: str, esp: str, payout: float
) -> list[dict[str, object]]:
    """Diagnóstico pedido pelo cliente (§9c.1): taxa por ordem do toque, sem direito a aprovação."""
    saida: list[dict[str, object]] = []
    ordem = p.eventos["ordem_toque"].to_numpy()
    for rotulo, faixa in (("2º", (2, 2)), ("3º", (3, 3)), ("4º", (4, 4)), ("5º+", (5, math.inf))):
        sel = m & (ordem >= faixa[0]) & (ordem <= faixa[1])
        if not sel.any():
            continue
        met = calcular(_ops_chave(p, exp, sel, janela), payout)
        saida.append(
            {"ativo": p.ativo, "variacao": var, "espelho": esp, "toque": rotulo,
             "n": met.wins + met.losses, "taxa": met.taxa}
        )  # fmt: skip
    return saida
