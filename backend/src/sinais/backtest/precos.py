"""Série de preços de referência para liquidação simulada."""

from __future__ import annotations

import numpy as np
import pandas as pd

from sinais.core.tempo import InstanteMs


class SeriePrecos:
    """Preço em um instante.

    - Granularidade 1 s: fechamento do candle de 1 s que termina em ``t`` (ou o mais recente
      até 2 s antes).
    - Granularidade 1 min: só nas fronteiras de minuto. Abertura do minuto que começa em ``t``;
      se não houver, fechamento do que termina em ``t``. Aproximação declarada no relatório.
    """

    def __init__(
        self, aberturas: np.ndarray, abre: np.ndarray, fecha: np.ndarray, granularidade_ms: int
    ) -> None:
        self._t = aberturas
        self._o = abre
        self._c = fecha
        self.granularidade_ms = granularidade_ms

    @classmethod
    def de_quadro(cls, df: pd.DataFrame, intervalo_ms: int) -> SeriePrecos:
        ordenado = df.sort_index()
        return cls(
            ordenado.index.to_numpy(dtype="int64"),
            ordenado["o"].to_numpy(dtype="float64"),
            ordenado["c"].to_numpy(dtype="float64"),
            intervalo_ms,
        )

    def _indice(self, abertura: int) -> int | None:
        i = int(np.searchsorted(self._t, abertura))
        return i if i < len(self._t) and self._t[i] == abertura else None

    def preco_em(self, t: InstanteMs) -> float | None:
        g = self.granularidade_ms
        if g == 1000:
            i = int(np.searchsorted(self._t, t - g, side="right")) - 1
            if i >= 0 and self._t[i] >= t - 3 * g:
                return float(self._c[i])
            return None
        if t % g:
            return None
        k = self._indice(t)
        if k is not None:
            return float(self._o[k])
        j = self._indice(t - g)
        return float(self._c[j]) if j is not None else None
