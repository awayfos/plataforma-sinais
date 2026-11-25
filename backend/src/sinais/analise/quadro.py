"""Conversão de candles para o quadro (DataFrame) usado pela análise."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from sinais.dados.modelos import Candle

COLUNAS = ("o", "h", "l", "c", "v", "vb")


def para_quadro(candles: Sequence[Candle]) -> pd.DataFrame:
    """Colunas ``o,h,l,c,v,vb`` em float64; índice ``abertura`` (ms UTC). ``Decimal`` vira float
    só aqui: a análise usa float, a liquidação continua em ``Decimal``."""
    dados = {
        "o": [float(c.abertura_preco) for c in candles],
        "h": [float(c.maxima) for c in candles],
        "l": [float(c.minima) for c in candles],
        "c": [float(c.fechamento) for c in candles],
        "v": [float(c.volume) for c in candles],
        "vb": [float(c.volume_compra_agressora) for c in candles],
    }
    indice = pd.Index([c.abertura for c in candles], name="abertura", dtype="int64")
    return pd.DataFrame(dados, index=indice, dtype="float64")
