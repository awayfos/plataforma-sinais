"""Conjunto de features ``fs-2`` = ``fs-1`` + microestrutura de 1 s + calendário.

O ``fs-1`` não muda: ``fs-2`` só acrescenta colunas à direita. Microestrutura e calendário do
minuto ``t`` referem-se ao instante de decisão ``t + 60 s``.
"""

from __future__ import annotations

import pandas as pd

from sinais.features.microestrutura import agregar_segundos, features_microestrutura
from sinais.features.snapshot import montar_snapshot

FEATURE_SET_VERSION_FS2 = "fs-2"
_MINUTO_MS = 60_000


def features_calendario(indice: pd.Index) -> pd.DataFrame:
    """Hora (UTC), minuto da hora e dia da semana do instante de decisão. O minuto da hora diz
    onde a decisão cai na grade de vencimento (ex.: tempo restante até o vencimento de 5 min)."""
    decisao = pd.to_datetime(indice.to_numpy(dtype="int64") + _MINUTO_MS, unit="ms", utc=True)
    return pd.DataFrame(
        {
            "cal_hora": decisao.hour,
            "cal_min_hora": decisao.minute,
            "cal_dia_semana": decisao.dayofweek,
        },
        index=indice,
    ).astype("float64")


def combinar_fs2(fs1: pd.DataFrame, micro: pd.DataFrame) -> pd.DataFrame:
    """Junta no índice do ``fs-1``; minuto sem segundos fica NaN."""
    return pd.concat([fs1, micro.reindex(fs1.index).astype(fs1.dtypes.iloc[0]), _cal(fs1)], axis=1)


def _cal(fs1: pd.DataFrame) -> pd.DataFrame:
    return features_calendario(fs1.index).astype(fs1.dtypes.iloc[0])


def montar_snapshot_fs2(df_1m: pd.DataFrame, df_1s: pd.DataFrame) -> pd.DataFrame:
    """Versão direta, para séries que cabem na memória (testes e cálculo ao vivo)."""
    return combinar_fs2(montar_snapshot(df_1m), features_microestrutura(agregar_segundos(df_1s)))
