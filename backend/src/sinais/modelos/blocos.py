"""Snapshot de séries longas em blocos, para caber na memória.

Cada bloco recebe ``JANELA_AO_VIVO_1M`` minutos de aquecimento antes dele; o teste da Fase 4
garante que, com esse aquecimento, o resultado bate com o cálculo sobre a série inteira.
"""

from __future__ import annotations

import pandas as pd

from sinais.features.snapshot import JANELA_AO_VIVO_1M, montar_snapshot


def montar_snapshot_em_blocos(df_1m: pd.DataFrame, bloco: int = 130_000) -> pd.DataFrame:
    partes = []
    for inicio in range(0, len(df_1m), bloco):
        ini_aquec = max(0, inicio - JANELA_AO_VIVO_1M)
        trecho = montar_snapshot(df_1m.iloc[ini_aquec : inicio + bloco])
        partes.append(trecho.iloc[inicio - ini_aquec :].astype("float32"))
    return pd.concat(partes)
