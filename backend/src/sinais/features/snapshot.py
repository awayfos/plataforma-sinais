"""Snapshot de features multi-tempo-gráfico (conjunto ``fs-1``).

``features_de`` junta todas as famílias de análise em colunas numéricas e estacionárias
(distâncias em ATR, razões, rótulos). ``montar_snapshot`` acrescenta o contexto de tempos
gráficos maiores usando, em cada minuto, só o último candle maior **já fechado**.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from sinais.analise import indicadores as ind
from sinais.analise import padroes_candle as pc
from sinais.analise import volume as vol
from sinais.analise.estrutura import estrutura
from sinais.analise.fibonacci import posicao_fibonacci
from sinais.analise.price_action import price_action
from sinais.analise.regioes import regioes
from sinais.core.dominio import TempoGrafico, abertura_candle

FEATURE_SET_VERSION = "fs-1"
_MINUTO_MS = 60_000
# Minutos de histórico que o cálculo ao vivo precisa para reproduzir o laboratório
# (300 candles de 1h: aquecimento de EMA50, ADX e Ichimoku do contexto mais longo).
JANELA_AO_VIVO_1M = 18_000
CONTEXTOS_PADRAO = (TempoGrafico.M5, TempoGrafico.M15, TempoGrafico.H1)


def _por_atr(x: pd.Series, a: pd.Series) -> pd.Series:
    return x / a.where(a > 0)


def features_de(df: pd.DataFrame) -> pd.DataFrame:
    c = df["c"]
    a = ind.atr(df)
    bb = ind.bollinger(c)
    faixa_bb = bb["sup"] - bb["inf"]
    ich = ind.ichimoku(df)
    e = estrutura(df)
    colunas: dict[str, pd.Series] = {
        "ind_rsi": ind.rsi(c),
        **{f"ind_macd_{k}": _por_atr(v, a) for k, v in ind.macd(c).items()},
        "ind_bb_pct": (c - bb["inf"]) / faixa_bb.where(faixa_bb > 0),
        "ind_bb_largura": bb["largura"],
        "ind_atr_rel": a / c.where(c > 0),
        **{f"ind_{k}": v for k, v in ind.adx(df).items()},
        **{f"ind_estoc_{k}": v for k, v in ind.estocastico(df).items()},
        "ind_ema20_dist": _por_atr(c - ind.ema(c, 20), a),
        "ind_ema50_dist": _por_atr(c - ind.ema(c, 50), a),
        "ind_ich_tk": _por_atr(ich["tenkan"] - ich["kijun"], a),
        "ind_ich_span_a": _por_atr(c - ich["span_a"], a),
        "ind_ich_span_b": _por_atr(c - ich["span_b"], a),
        "pad_doji": pc.doji(df),
        "pad_martelo": pc.martelo(df),
        "pad_estrela_cadente": pc.estrela_cadente(df),
        "pad_pin_bar": pc.pin_bar(df),
        "pad_engolfo": pc.engolfo(df),
        "pad_marubozu": pc.marubozu(df),
        "pad_inside": pc.inside_bar(df),
        "pad_outside": pc.outside_bar(df),
        "pad_estrela_manha": pc.estrela_manha(df),
        "pad_estrela_tarde": pc.estrela_tarde(df),
        "pad_sequencia": pc.sequencia(df),
        **{f"pad_{k}": v for k, v in pc.forca(df).items()},
        **{f"est_{k}": e[k] for k in ("rotulo_topo", "rotulo_fundo", "tendencia", "bos", "choch")},
        "est_dist_topo": _por_atr(e["ultimo_topo"] - c, a),
        "est_dist_fundo": _por_atr(c - e["ultimo_fundo"], a),
        "vol_relativo": vol.volume_relativo(df),
        "vol_expansao": vol.expansao_volume(df),
        "vol_pressao": vol.pressao_acumulada(df),
        "vol_divergencia": vol.divergencia_volume(df),
        "vol_vwap_dist": _por_atr(c - vol.vwap(df), a),
        **{f"reg_{k}": v for k, v in regioes(df).items()},
        "fib_posicao": posicao_fibonacci(df, est=e),
        **{f"pa_{k}": v for k, v in price_action(df, est=e).items()},
    }
    return pd.DataFrame(colunas, index=df.index).astype("float64")


def agregar_quadro(df_1m: pd.DataFrame, tg: TempoGrafico) -> pd.DataFrame:
    """Agrega 1m em ``tg``; só blocos completos (todos os minutos presentes)."""
    blocos = pd.Index([abertura_candle(int(t), tg) for t in df_1m.index], name="abertura")
    g = df_1m.groupby(blocos)
    agregado = pd.DataFrame(
        {
            "o": g["o"].first(),
            "h": g["h"].max(),
            "l": g["l"].min(),
            "c": g["c"].last(),
            "v": g["v"].sum(),
            "vb": g["vb"].sum(),
        }
    )
    completos = g.size() == tg.duracao_ms // _MINUTO_MS
    return agregado[completos]


def montar_snapshot(
    df_1m: pd.DataFrame, contextos: Sequence[TempoGrafico] = CONTEXTOS_PADRAO
) -> pd.DataFrame:
    base = features_de(df_1m)
    fechamento_1m = df_1m.index.to_numpy(dtype="int64") + _MINUTO_MS
    partes = [base]
    for tg in contextos:
        prefixo = f"{tg.name.lower()}_"
        agregado = agregar_quadro(df_1m, tg)
        ctx = features_de(agregado).add_prefix(prefixo)
        ctx["_fech_ctx"] = agregado.index.to_numpy(dtype="int64") + tg.duracao_ms
        alvo = pd.DataFrame({"_fech": fechamento_1m})
        juntado = pd.merge_asof(
            alvo, ctx, left_on="_fech", right_on="_fech_ctx", direction="backward"
        )
        juntado.index = df_1m.index
        idade = (juntado["_fech"] - juntado["_fech_ctx"]) / _MINUTO_MS
        # Contexto mais velho que a própria duração = lacuna nos dados: não usar.
        vencido = idade >= tg.duracao_ms // _MINUTO_MS
        juntado = juntado.drop(columns=["_fech", "_fech_ctx"])
        juntado[vencido] = np.nan
        juntado[f"{prefixo}idade_ctx"] = idade
        partes.append(juntado)
    saida = pd.concat(partes, axis=1)
    return saida.astype("float64").replace([np.inf, -np.inf], np.nan)
