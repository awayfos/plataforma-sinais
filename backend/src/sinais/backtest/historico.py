"""Histórico oficial da Binance em arquivos mensais (data.binance.vision).

CSV sem cabeçalho, 12 colunas, como no REST. A partir de 2025 o tempo vem em microssegundos.
Mês ausente (404) vira lacuna registrada, sem interromper a carga.
"""

from __future__ import annotations

import io
import zipfile
from collections.abc import Sequence

import httpx
import pandas as pd

BASE = "https://data.binance.vision/data/spot/monthly/klines"
_NOMES = ["abertura", "o", "h", "l", "c", "v", "fechamento", "vq", "n", "vb", "vbq", "x"]


def url_mensal(simbolo: str, intervalo: str, ano: int, mes: int) -> str:
    return f"{BASE}/{simbolo}/{intervalo}/{simbolo}-{intervalo}-{ano:04d}-{mes:02d}.zip"


def ler_csv_klines(texto: str) -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(texto), header=None, names=_NOMES)
    abertura = df["abertura"].astype("int64")
    if len(abertura) and abertura.iloc[0] > 10**14:  # microssegundos
        abertura = abertura // 1000
    saida = df[["o", "h", "l", "c", "v", "vb"]].astype("float64")
    saida.index = pd.Index(abertura.to_numpy(), name="abertura")
    return saida


async def baixar_meses(
    http: httpx.AsyncClient, simbolo: str, intervalo: str, meses: Sequence[tuple[int, int]]
) -> tuple[pd.DataFrame, list[str]]:
    partes: list[pd.DataFrame] = []
    lacunas: list[str] = []
    for ano, mes in meses:
        r = await http.get(url_mensal(simbolo, intervalo, ano, mes), timeout=60)
        if r.status_code == 404:
            lacunas.append(f"{simbolo} {intervalo} {ano:04d}-{mes:02d}")
            continue
        r.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            for nome in z.namelist():
                partes.append(ler_csv_klines(z.read(nome).decode()))
    if not partes:
        return pd.DataFrame(columns=["o", "h", "l", "c", "v", "vb"], dtype="float64"), lacunas
    df = pd.concat(partes)
    return df[~df.index.duplicated()].sort_index(), lacunas
