"""Klines de 1 s do histórico oficial da Binance, um mês por vez.

Um mês de 1 s tem cerca de 2,6 milhões de linhas. ``ler_zip_1s`` lê direto do zip, só as
colunas usadas (inclusive o número de negócios ``n``), sem montar o texto inteiro na memória.
"""

from __future__ import annotations

import io
import zipfile

import httpx
import pandas as pd

from sinais.backtest.historico import url_mensal

# posições no CSV de 12 colunas: abertura, o, h, l, c, v, ..., n (8), vb (9)
_USADAS = [0, 1, 2, 3, 4, 5, 8, 9]
_NOMES = ["abertura", "o", "h", "l", "c", "v", "n", "vb"]


def ler_zip_1s(conteudo: bytes) -> pd.DataFrame:
    partes = []
    with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
        for nome in z.namelist():
            with z.open(nome) as f:
                df = pd.read_csv(f, header=None, usecols=_USADAS, names=_NOMES)
            abertura = df["abertura"].to_numpy(dtype="int64")
            if len(abertura) and abertura[0] > 10**14:  # microssegundos (2025+)
                abertura = abertura // 1000
            saida = df[["o", "h", "l", "c", "v", "vb", "n"]].astype("float64")
            saida.index = pd.Index(abertura, name="abertura")
            partes.append(saida)
    df = pd.concat(partes) if len(partes) > 1 else partes[0]
    return df[~df.index.duplicated()].sort_index()


async def baixar_mes_1s(  # pragma: no cover - rede
    http: httpx.AsyncClient, simbolo: str, ano: int, mes: int
) -> pd.DataFrame | None:
    """None quando o mês não existe (404): vira lacuna registrada pelo chamador."""
    r = await http.get(url_mensal(simbolo, "1s", ano, mes), timeout=600)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return ler_zip_1s(r.content)
