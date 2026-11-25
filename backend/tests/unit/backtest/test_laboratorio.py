import asyncio
import io
import zipfile

import numpy as np
import pytest

pytest.importorskip("httpx")

import httpx  # noqa: E402

from sinais.backtest.historico import baixar_meses, ler_csv_klines, url_mensal  # noqa: E402
from sinais.backtest.laboratorio import avaliar  # noqa: E402
from sinais.backtest.relatorio import gerar_markdown  # noqa: E402

from ..analise.sinteticos import T0, M, passeio  # noqa: E402

LINHA_MS = f"{T0},100.0,101.0,99.0,100.5,12.5,{T0 + M - 1},1250.0,30,6.25,625.0,0\n"
LINHA_US = f"{T0 * 1000},100.0,101.0,99.0,100.5,12.5,{(T0 + M) * 1000 - 1},1250.0,30,6.25,625.0,0\n"


def test_url_mensal() -> None:
    assert url_mensal("BTCUSDT", "1m", 2025, 3) == (
        "https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-2025-03.zip"
    )


@pytest.mark.parametrize("linha", [LINHA_MS, LINHA_US])
def test_ler_csv_em_ms_e_us(linha: str) -> None:
    df = ler_csv_klines(linha)
    assert df.index.tolist() == [T0]
    assert df.loc[T0, "c"] == 100.5
    assert df.loc[T0, "vb"] == 6.25


def zip_com(nome: str, texto: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(nome, texto)
    return buf.getvalue()


def test_mes_faltando_vira_lacuna() -> None:
    def h(r: httpx.Request) -> httpx.Response:
        if r.url.path.endswith("2025-02.zip"):
            return httpx.Response(404)
        return httpx.Response(200, content=zip_com("x.csv", LINHA_MS))

    async def caso() -> tuple[int, list[str]]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(h)) as http:
            df, lacunas = await baixar_meses(http, "BTCUSDT", "1m", [(2025, 1), (2025, 2)])
        return len(df), lacunas

    n, lacunas = asyncio.run(caso())
    assert n == 1
    assert lacunas == ["BTCUSDT 1m 2025-02"]


def test_avaliar_e_relatorio_com_hipoteses() -> None:
    linhas = avaliar(passeio(3000, semente=2), "SINTETICO", payout=0.85)
    estrategias = {linha.estrategia for linha in linhas}
    assert {"sempre_compra", "sempre_venda", "seguir_ultimo", "aleatoria"} <= estrategias
    assert all(linha.metricas.n > 0 for linha in linhas if linha.expiracao == "1m")
    texto = gerar_markdown(linhas, {"payout": "0.85 (hipotético)", "fonte": "sintético"})
    assert "0.85 (hipotético)" in texto
    assert "| SINTETICO |" in texto
    assert not np.isnan(linhas[0].metricas.p_equilibrio)
