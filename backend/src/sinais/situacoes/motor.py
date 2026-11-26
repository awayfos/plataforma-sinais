"""Motor de situações: roda todos os detectores e acrescenta o contexto comum.

- ``dist_sr_atr``: distância, em ATR de 1m, ao suporte/resistência mais próximo de
  ``analise.regioes`` no candle da decisão;
- ``queda_pressao``: sinal × (pressão média dos 5 candles anteriores − pressão do candle da
  decisão), sinal +1 no topo e −1 no fundo (positivo = o lado do rompimento perdeu força);
- ``confluencias``: quantas **outras** variações dispararam na mesma direção em
  (decisão − 15 min, decisão];
- ``conflito``: existe evento de direção oposta na mesma decisão (design §9b.6: AGUARDAR).
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from sinais.analise.regioes import regioes
from sinais.situacoes import detectores as det
from sinais.situacoes.base import Base, montar_base
from sinais.situacoes.eventos import quadro_eventos
from sinais.situacoes.parametros import (
    CONFLUENCIA_JANELA_MIN,
    MINUTO_MS,
    QUEDA_PRESSAO_CANDLES,
    VARIACOES,
    ParamS1,
    ParamS2,
    ParamS3,
    ParamS4,
    ParamS5,
    ParamS6,
    ParamS7,
    ParamS8,
    Variacao,
)


def _detectar(
    base: Base, v: Variacao, cache: dict[tuple[int, float, int], dict[int, list[det.Rompimento]]]
) -> list[det.Linha]:
    p = v.parametros
    if isinstance(p, ParamS1):
        return det.detectar_s1(base, p, v.nome)
    if isinstance(p, ParamS2 | ParamS3):
        chave = (p.k_pivo, p.tolerancia_atr, p.janela_toques_min)
        if chave not in cache:
            cache[chave] = det.rompimentos(base, *chave)
        romp = cache[chave]
        if isinstance(p, ParamS2):
            return det.detectar_s2(base, p, v.nome, romp)
        return det.detectar_s3(base, p, v.nome, romp)
    if isinstance(p, ParamS4):
        return det.detectar_s4(base, p, v.nome)
    if isinstance(p, ParamS5):
        return det.detectar_s5(base, p, v.nome)
    if isinstance(p, ParamS6):
        return det.detectar_s6(base, p, v.nome)
    if isinstance(p, ParamS7):
        return det.detectar_s7(base, p, v.nome)
    if isinstance(p, ParamS8):
        return det.detectar_s8(base, p, v.nome)
    raise TypeError(f"parâmetros desconhecidos: {p!r}")


def marcar_confluencia_e_conflito(ev: pd.DataFrame) -> pd.DataFrame:
    """Preenche ``confluencias`` e ``conflito`` (só olha decisões até a do próprio evento)."""
    ev = ev.copy()
    d = ev["decisao"].to_numpy(dtype="int64")
    direcao = ev["direcao"].to_numpy(dtype="int64")
    var = ev["variacao"].to_numpy()
    janela = CONFLUENCIA_JANELA_MIN * MINUTO_MS
    conf = np.zeros(len(ev), dtype="int64")
    conflito = np.zeros(len(ev), dtype="bool")
    ordem = np.argsort(d, kind="stable")
    ds = d[ordem]
    for i in ordem:
        ini = int(np.searchsorted(ds, d[i] - janela, side="right"))
        fim = int(np.searchsorted(ds, d[i], side="right"))
        vizinhos = ordem[ini:fim]
        mesma = vizinhos[(direcao[vizinhos] == direcao[i]) & (var[vizinhos] != var[i])]
        conf[i] = len(set(var[mesma].tolist()))
        no_minuto = vizinhos[d[vizinhos] == d[i]]
        conflito[i] = bool((direcao[no_minuto] != direcao[i]).any())
    ev["confluencias"] = conf
    ev["conflito"] = conflito
    return ev


def detectar_todas(df_1m: pd.DataFrame, variacoes: Sequence[Variacao] = VARIACOES) -> pd.DataFrame:
    base = montar_base(df_1m)
    cache: dict[tuple[int, float, int], dict[int, list[det.Rompimento]]] = {}
    linhas = [linha for v in variacoes for linha in _detectar(base, v, cache)]
    ev = quadro_eventos(linhas)
    if ev.empty:
        return ev
    i = np.searchsorted(base.decisao, ev["decisao"].to_numpy(dtype="int64"))
    reg = regioes(df_1m)
    ev["dist_sr_atr"] = np.fmin(reg["res_dist"].to_numpy()[i], reg["sup_dist"].to_numpy()[i])
    n = QUEDA_PRESSAO_CANDLES
    media_ant = pd.Series(base.pressao).rolling(n, min_periods=n).mean().shift(1).to_numpy()
    sinal = np.where(ev["espelho"].to_numpy() == "topo", 1.0, -1.0)
    ev["queda_pressao"] = sinal * (media_ant[i] - base.pressao[i])
    return marcar_confluencia_e_conflito(ev)
