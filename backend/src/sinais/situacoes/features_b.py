"""Variáveis da camada B: ``fs-2`` no minuto da decisão + contexto da situação (design §5, §9c).

``snapshot_fs2_nas_linhas`` calcula o ``fs-1`` em blocos (como ``modelos.blocos``, com o mesmo
aquecimento) e guarda só as linhas pedidas, para não manter 247 colunas × 1 milhão de minutos na
memória.
"""

from __future__ import annotations

import pandas as pd

from sinais.features.fs2 import combinar_fs2
from sinais.features.snapshot import JANELA_AO_VIVO_1M, montar_snapshot
from sinais.modelos.treino import colunas_modelo

_MINUTO_MS = 60_000
COLUNAS_CONTEXTO = [
    "ordem_toque",
    "min_entre_toques",
    "dist_sr_atr",
    "queda_pressao",
    "confluencias",
    "espelho_id",
    "ativo_id",
    "direcao",
    "tempo_restante_s",
]
ATIVO_ID = {"BTCUSDT": 0.0, "ETHUSDT": 1.0}


def snapshot_fs2_nas_linhas(
    df_1m: pd.DataFrame, micro: pd.DataFrame, linhas: pd.Index, bloco: int = 130_000
) -> pd.DataFrame:
    """``fs-2`` (float32) nas aberturas ``linhas`` de ``df_1m``."""
    alvo = pd.Index(sorted(set(linhas)), dtype="int64", name="abertura")
    partes = []
    for inicio in range(0, len(df_1m), bloco):
        trecho_idx = df_1m.index[inicio : inicio + bloco]
        pedidas = alvo[(alvo >= trecho_idx[0]) & (alvo <= trecho_idx[-1])]
        if not len(pedidas):
            continue
        ini_aquec = max(0, inicio - JANELA_AO_VIVO_1M)
        trecho = montar_snapshot(df_1m.iloc[ini_aquec : inicio + bloco])
        partes.append(trecho.loc[pedidas])
    fs1 = pd.concat(partes) if partes else montar_snapshot(df_1m.iloc[:0])
    return combinar_fs2(fs1, micro).astype("float32")


def matriz_b(eventos: pd.DataFrame, snapshot: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Linhas de ``eventos`` (com ``ativo``) + ``fs-2`` do minuto da decisão + contexto."""
    abertura = eventos["decisao"].to_numpy(dtype="int64") - _MINUTO_MS
    snap = snapshot[colunas_modelo(snapshot)].reindex(abertura)
    snap.index = eventos.index
    ctx = pd.DataFrame(
        {
            "ordem_toque": eventos["ordem_toque"],
            "min_entre_toques": eventos["min_entre_toques"],
            "dist_sr_atr": eventos["dist_sr_atr"],
            "queda_pressao": eventos["queda_pressao"],
            "confluencias": eventos["confluencias"],
            "espelho_id": (eventos["espelho"] == "topo").astype("float64"),
            "ativo_id": eventos["ativo"].map(ATIVO_ID).astype("float64"),
            "direcao": eventos["direcao"],
            "tempo_restante_s": (eventos["vencimento_t"] - eventos["decisao"]) / 1000,
        },
        index=eventos.index,
    ).astype("float64")
    x = pd.concat([snap.astype("float64"), ctx], axis=1)
    return x, list(x.columns)
