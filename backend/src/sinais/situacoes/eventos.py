"""Esquema dos eventos de situação (uma linha por disparo)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pandas as pd

COLUNAS_EVENTO = [
    "decisao",  # ms: fechamento do candle de 1m da confirmação
    "situacao",
    "variacao",
    "espelho",  # "topo" | "fundo"
    "direcao",  # +1 compra, −1 venda
    "nivel",  # preço de referência (topo, nível rompido, zona…)
    "ordem_toque",
    "min_entre_toques",
    "dist_sr_atr",
    "queda_pressao",
    "confluencias",
    "conflito",
]
_TIPOS = {
    "decisao": "int64",
    "situacao": "object",
    "variacao": "object",
    "espelho": "object",
    "direcao": "int64",
    "nivel": "float64",
    "ordem_toque": "float64",
    "min_entre_toques": "float64",
    "dist_sr_atr": "float64",
    "queda_pressao": "float64",
    "confluencias": "int64",
    "conflito": "bool",
}
_PADRAO: dict[str, Any] = {
    "nivel": float("nan"),
    "ordem_toque": float("nan"),
    "min_entre_toques": float("nan"),
    "dist_sr_atr": float("nan"),
    "queda_pressao": float("nan"),
    "confluencias": 0,
    "conflito": False,
}


def evento(
    decisao: int, variacao: str, situacao: str, espelho: str, **contexto: float
) -> dict[str, Any]:
    direcao_topo = {"S3": 1, "S4": 1}.get(situacao, -1)
    direcao = direcao_topo if espelho == "topo" else -direcao_topo
    return {
        **_PADRAO,
        "decisao": int(decisao),
        "situacao": situacao,
        "variacao": variacao,
        "espelho": espelho,
        "direcao": direcao,
        **contexto,
    }


def quadro_eventos(linhas: Sequence[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(list(linhas), columns=COLUNAS_EVENTO)
    for coluna, valor in _PADRAO.items():
        df[coluna] = (
            df[coluna].fillna(valor) if coluna in ("confluencias", "conflito") else df[coluna]
        )
    return df.astype(_TIPOS).sort_values(["decisao", "variacao", "espelho"], ignore_index=True)
