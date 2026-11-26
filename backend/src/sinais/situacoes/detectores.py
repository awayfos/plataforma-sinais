"""Detectores causais das situações S1–S8 (regras pré-registradas em ``parametros.py``).

Cada detector percorre os candles de 1m em ordem e, no candle ``i``, usa só candles de 1m até ``i``
e blocos de 5m/15m já fechados até a decisão (``base.idx5``/``base.idx15``). Devolve linhas de
evento (``eventos.evento``) com a decisão no fechamento do candle de confirmação. Pressão
indefinida (volume zero) nunca satisfaz uma condição de pressão.

Espelho "topo" = situação num topo/resistência; "fundo" = o reflexo exato (preço invertido, compra
↔ venda agressora). A direção vem de ``eventos.evento``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from sinais.analise import padroes_candle as pc
from sinais.analise.estrutura import estrutura, pivos
from sinais.analise.indicadores import adx, rsi
from sinais.situacoes.base import Base
from sinais.situacoes.eventos import evento
from sinais.situacoes.parametros import (
    MINUTO_MS,
    ParamS1,
    ParamS2,
    ParamS3,
    ParamS4,
    ParamS5,
)
from sinais.situacoes.zonas import Zonas

Linha = dict[str, Any]


def _ge(x: float, limite: float) -> bool:
    return not math.isnan(x) and x >= limite


def _le(x: float, limite: float) -> bool:
    return not math.isnan(x) and x <= limite


def _gt(x: float, limite: float) -> bool:
    return not math.isnan(x) and x > limite


def _lt(x: float, limite: float) -> bool:
    return not math.isnan(x) and x < limite


# ---------------------------------------------------------------- S1


def detectar_s1(base: Base, p: ParamS1, nome: str = "S1") -> list[Linha]:
    h, lo, c, pr = base.h, base.l, base.c, base.pressao
    maxima_ant = pd.Series(h).rolling(p.janela_min, min_periods=p.janela_min).max().shift(1)
    minima_ant = pd.Series(lo).rolling(p.janela_min, min_periods=p.janela_min).min().shift(1)
    mx, mn = maxima_ant.to_numpy(), minima_ant.to_numpy()
    saida: list[Linha] = []
    topo: tuple[int, float, float] | None = None  # (candle do topo, máxima, mínima)
    fundo: tuple[int, float, float] | None = None
    for i in range(len(c)):
        if topo is not None:
            s, alto, baixo = topo
            if h[i] > alto:
                topo = None
            else:
                fracos = sum(
                    1 for j in range(s + 1, min(s + p.candles_fraqueza, i) + 1)
                    if _lt(pr[j], p.pressao_fraca)
                )  # fmt: skip
                if fracos >= p.minimo_fracos and c[i] < baixo:
                    saida.append(evento(base.decisao[i], nome, "S1", "topo", nivel=alto))
                    topo = None
                elif i - s >= p.confirmacao_min:
                    topo = None
        if fundo is not None:
            s, alto, baixo = fundo
            if lo[i] < baixo:
                fundo = None
            else:
                fortes = sum(
                    1 for j in range(s + 1, min(s + p.candles_fraqueza, i) + 1)
                    if _gt(pr[j], 1 - p.pressao_fraca)
                )  # fmt: skip
                if fortes >= p.minimo_fracos and c[i] > alto:
                    saida.append(evento(base.decisao[i], nome, "S1", "fundo", nivel=baixo))
                    fundo = None
                elif i - s >= p.confirmacao_min:
                    fundo = None
        if h[i] > mx[i]:  # NaN (aquecimento) nunca é máxima nova
            topo = (i, h[i], lo[i]) if _ge(pr[i], p.pressao_rompimento) else None
        if lo[i] < mn[i]:
            fundo = (i, h[i], lo[i]) if _le(pr[i], 1 - p.pressao_rompimento) else None
    return saida


# ---------------------------------------------------------------- regiões (S2, S3)


@dataclass(frozen=True)
class Rompimento:
    lado: int  # +1 fechou acima de uma resistência, −1 abaixo de um suporte
    preco: float
    toques: int
    min_entre_toques: float


def rompimentos(
    base: Base, k: int, tolerancia_atr: float, janela_min: int
) -> dict[int, list[Rompimento]]:
    """Por candle ``i``: níveis cruzados pelo fechamento (``c[i-1]`` → ``c[i]``), com os níveis e
    toques conhecidos até ``i - 1`` (pivôs de 1m confirmados ``k`` candles depois)."""
    piv = pivos(base.df, k)
    topos, fundos = piv["topo"].to_numpy(), piv["fundo"].to_numpy()
    janela = janela_min * MINUTO_MS
    zonas = Zonas()
    saida: dict[int, list[Rompimento]] = {}
    c, t, a = base.c, base.t, base.atr1
    for i in range(len(c)):
        if i > 0:
            achados = []
            for n in zonas.rompidos(c[i - 1], c[i]):
                lado = 1 if c[i] > c[i - 1] else -1
                achados.append(
                    Rompimento(
                        lado,
                        n.preco,
                        zonas.toques_em(n, int(t[i]), janela),
                        zonas.min_entre_toques(n, int(t[i]), janela),
                    )
                )
            if achados:
                saida[i] = achados
        tol = tolerancia_atr * a[i] if not math.isnan(a[i]) else 0.0
        for valores in (topos, fundos):
            if not math.isnan(valores[i]):
                zonas.adicionar(float(valores[i]), tol, int(t[i - k]))
    return saida


def _melhor(candidatos: list[Rompimento], c: float) -> Rompimento:
    return max(candidatos, key=lambda r: (r.toques, -abs(r.preco - c)))


def detectar_s2(
    base: Base, p: ParamS2, nome: str = "S2", romp: dict[int, list[Rompimento]] | None = None
) -> list[Linha]:
    romp = (
        rompimentos(base, p.k_pivo, p.tolerancia_atr, p.janela_toques_min) if romp is None else romp
    )
    c = base.c
    pendentes: dict[int, tuple[int, Rompimento]] = {}  # lado → (candle do rompimento, nível)
    saida: list[Linha] = []
    for i in range(len(c)):
        for lado, (b, r) in list(pendentes.items()):
            if i - b > p.volta_max_candles:
                del pendentes[lado]
            elif (lado == 1 and c[i] < r.preco) or (lado == -1 and c[i] > r.preco):
                saida.append(
                    evento(
                        base.decisao[i], nome, "S2", "topo" if lado == 1 else "fundo",
                        nivel=r.preco, ordem_toque=r.toques + 1,
                        min_entre_toques=r.min_entre_toques,
                    )
                )  # fmt: skip
                del pendentes[lado]
        for lado in (1, -1):
            cand = [r for r in romp.get(i, []) if r.lado == lado and r.toques >= p.toques_min]
            if cand:
                pendentes[lado] = (i, _melhor(cand, c[i]))
    return saida


def detectar_s3(
    base: Base, p: ParamS3, nome: str = "S3", romp: dict[int, list[Rompimento]] | None = None
) -> list[Linha]:
    romp = (
        rompimentos(base, p.k_pivo, p.tolerancia_atr, p.janela_toques_min) if romp is None else romp
    )
    c, h, lo, a, pr, vr = base.c, base.h, base.l, base.atr1, base.pressao, base.vol_rel
    # lado → [candle do rompimento, nível, já se afastou do nível]
    pendentes: dict[int, tuple[int, Rompimento, bool]] = {}
    saida: list[Linha] = []
    for i in range(len(c)):
        for lado, (b, r, saiu) in list(pendentes.items()):
            perto = p.proximidade_atr * a[i]
            if i - b > p.reteste_max_min or math.isnan(perto):
                del pendentes[lado]
                continue
            if (lado == 1 and c[i] <= r.preco) or (lado == -1 and c[i] >= r.preco):
                del pendentes[lado]  # rompimento falhou
                continue
            reteste = lo[i] <= r.preco + perto if lado == 1 else h[i] >= r.preco - perto
            if saiu and reteste:
                saida.append(
                    evento(
                        base.decisao[i], nome, "S3", "topo" if lado == 1 else "fundo",
                        nivel=r.preco, ordem_toque=r.toques + 1,
                        min_entre_toques=r.min_entre_toques,
                    )
                )  # fmt: skip
                del pendentes[lado]
                continue
            longe = lo[i] > r.preco + perto if lado == 1 else h[i] < r.preco - perto
            pendentes[lado] = (b, r, saiu or longe)
        if _ge(vr[i], p.volume_rel_min):
            for lado in (1, -1):
                forca = _ge(pr[i], p.pressao_min) if lado == 1 else _le(pr[i], 1 - p.pressao_min)
                cand = [r for r in romp.get(i, []) if r.lado == lado and r.toques >= p.toques_min]
                if forca and cand:
                    pendentes[lado] = (i, _melhor(cand, c[i]), False)
    return saida


# ---------------------------------------------------------------- 5m (S4, S5)


def _blocos_novos(idx: np.ndarray) -> np.ndarray:
    """``novo[i]`` = posição do bloco que acabou de fechar no candle ``i`` (ou −1)."""
    anterior = np.concatenate([[-1], idx[:-1]])
    return np.where((idx >= 0) & (idx != anterior), idx, -1)


def detectar_s4(base: Base, p: ParamS4, nome: str = "S4") -> list[Linha]:
    e = estrutura(base.q5.df, p.k_pivo_5m)
    bos = e["bos"].to_numpy()
    topo, fundo = e["ultimo_topo"].to_numpy(), e["ultimo_fundo"].to_numpy()
    eng = pc.engolfo(base.df).to_numpy()
    pin = pc.pin_bar(base.df).to_numpy()
    novo = _blocos_novos(base.idx5)
    c, h, lo, a, d = base.c, base.h, base.l, base.atr1, base.decisao
    janela = p.janela_min * MINUTO_MS
    # lado → (nível rompido, fim da janela, já se afastou)
    setups: dict[int, tuple[float, int, bool]] = {}
    saida: list[Linha] = []
    for i in range(len(c)):
        for lado, (nivel, fim, saiu) in list(setups.items()):
            perto = p.proximidade_atr * a[i]
            if d[i] > fim or math.isnan(perto):
                del setups[lado]
                continue
            if (lado == 1 and c[i] < nivel) or (lado == -1 and c[i] > nivel):
                del setups[lado]
                continue
            if lado == 1:
                volta = lo[i] <= nivel + perto
                rejeita = eng[i] == 1 or pin[i] == 1
                longe = lo[i] > nivel + perto
            else:
                volta = h[i] >= nivel - perto
                rejeita = eng[i] == -1 or pin[i] == -1
                longe = h[i] < nivel - perto
            if saiu and volta and rejeita:
                espelho = "topo" if lado == 1 else "fundo"
                saida.append(evento(d[i], nome, "S4", espelho, nivel=nivel))
                del setups[lado]
                continue
            setups[lado] = (nivel, fim, saiu or longe)
        j = novo[i]
        if j >= 0 and bos[j] != 0:
            lado = int(bos[j])
            nivel = float(topo[j] if lado == 1 else fundo[j])
            setups[lado] = (nivel, int(base.q5.fech[j]) + janela, False)
    return saida


def _pivos_conhecidos(valores: np.ndarray, k: int) -> list[tuple[int, int]]:
    """(linha de confirmação, candle do pivô) em ordem."""
    return [(int(j), int(j) - k) for j in np.flatnonzero(~np.isnan(valores))]


def detectar_s5(base: Base, p: ParamS5, nome: str = "S5") -> list[Linha]:
    q5 = base.q5
    e = estrutura(q5.df, p.k_pivo_5m)
    choch = e["choch"].to_numpy()
    pv = pivos(q5.df, p.k_pivo_5m)
    topos, fundos = pv["topo"].to_numpy(), pv["fundo"].to_numpy()
    r = rsi(q5.df["c"]).to_numpy(dtype="float64") if len(q5.df) else np.zeros(0)
    a15 = (
        adx(base.q15.df)
        if len(base.q15.df)
        else pd.DataFrame(columns=["adx", "mais_di", "menos_di"])
    )
    adx15 = a15["adx"].to_numpy(dtype="float64")
    mais, menos = (
        a15["mais_di"].to_numpy(dtype="float64"),
        a15["menos_di"].to_numpy(dtype="float64"),
    )
    conf_t = _pivos_conhecidos(topos, p.k_pivo_5m)
    conf_f = _pivos_conhecidos(fundos, p.k_pivo_5m)
    novo = _blocos_novos(base.idx5)
    saida: list[Linha] = []

    def ultimos(conf: list[tuple[int, int]], j: int) -> list[int]:
        return [piv for linha, piv in conf if linha <= j][-2:]

    for i in np.flatnonzero(novo >= 0):
        j = int(novo[i])
        lado = int(choch[j])
        k15 = int(base.idx15[i])
        if lado == 0 or k15 < 0 or not _ge(adx15[k15], p.adx_min):
            continue
        if lado == -1:  # quebra para baixo após alta: topos mais altos com RSI menor
            if not mais[k15] > menos[k15]:
                continue
            ps = ultimos(conf_t, j)
            valores = topos
            ok = len(ps) == 2 and q5.h[ps[1]] > q5.h[ps[0]] and _lt(r[ps[1]], r[ps[0]])
        else:
            if not menos[k15] > mais[k15]:
                continue
            ps = ultimos(conf_f, j)
            valores = fundos
            ok = len(ps) == 2 and q5.l[ps[1]] < q5.l[ps[0]] and _gt(r[ps[1]], r[ps[0]])
        if ok and j - ps[1] <= p.idade_max_pivo_5m:
            nivel = float(valores[ps[1] + p.k_pivo_5m])
            espelho = "topo" if lado == -1 else "fundo"
            saida.append(evento(base.decisao[i], nome, "S5", espelho, nivel=nivel))
    return saida
