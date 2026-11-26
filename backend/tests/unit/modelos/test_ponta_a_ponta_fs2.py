"""Ponta a ponta com sinal plantado só na microestrutura, pelo mesmo caminho da produção:
zip de 1 s → ``ler_zip_1s`` → ``AgregadorMicro`` → ``montar_snapshot_em_blocos`` →
``combinar_fs2`` → ``avaliar_combinacao_v2``.

A direção do minuto m é sorteada (subida, queda ou parado); nos últimos 10 s do minuto
m − 1 toda a agressão é de compra (se m sobe) ou de venda (se m cai). Os candles de 1m não
carregam essa informação, então só um caminho de microestrutura sem defeito encontra o sinal
(prova contra falso negativo).
"""

import io
import zipfile
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from sinais.backtest.metricas import calcular
from sinais.backtest.precos import SeriePrecos
from sinais.core.dominio import Expiracao
from sinais.core.tempo import de_datetime
from sinais.features.fs2 import combinar_fs2
from sinais.features.microestrutura import AgregadorMicro, features_microestrutura
from sinais.modelos.avaliacao_v2 import avaliar_combinacao_v2
from sinais.modelos.blocos import montar_snapshot_em_blocos
from sinais.modelos.dados_1s import ler_zip_1s

MESES = [(2025, 2), (2025, 3), (2025, 4)]


def _inicio(ano: int, mes: int) -> int:
    return de_datetime(datetime(ano, mes, 1, tzinfo=UTC))


def _serie() -> pd.DataFrame:
    ini, fim = _inicio(2025, 2), _inicio(2025, 5)
    n_min = (fim - ini) // 60_000
    rng = np.random.default_rng(0)
    d = rng.choice([-1.0, 0.0, 1.0], n_min, p=[0.4, 0.2, 0.4])  # 0: minuto parado (apertado)
    passo = np.repeat(d * 0.05, 60) + rng.normal(0, 0.02, n_min * 60)
    c = np.round(10_000 + np.cumsum(passo), 2)
    v = rng.exponential(1.0, n_min * 60) + 0.01
    vb = v / 2
    s = np.tile(np.arange(60), n_min)
    prox = np.repeat(np.r_[d[1:], 0.0], 60)  # direção do minuto seguinte
    vb = np.where((s >= 50) & (prox != 0), np.where(prox > 0, v, 0.0), vb)
    t = ini + np.arange(n_min * 60, dtype="int64") * 1000
    o = np.r_[c[0], c[:-1]]
    return pd.DataFrame(
        {"t": t, "o": o, "h": np.maximum(o, c), "l": np.minimum(o, c), "c": c, "v": v, "vb": vb}
    )


def _zip_mes(df: pd.DataFrame) -> bytes:
    csv = pd.DataFrame(
        {
            "abertura": df["t"] * 1000,  # microssegundos, como a Binance desde 2025
            "o": df["o"], "h": df["h"], "l": df["l"], "c": df["c"], "v": df["v"],
            "fech": df["t"] * 1000 + 999_999, "vq": 0, "n": 5, "vb": df["vb"], "vbq": 0, "x": 0,
        }
    ).to_csv(header=False, index=False, float_format="%.6g")  # fmt: skip
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        z.writestr("X-1s.csv", csv)
    return buf.getvalue()


def test_sinal_so_na_microestrutura_e_encontrado_pelo_caminho_de_producao() -> None:
    serie = _serie()
    agregador = AgregadorMicro()
    ts, cs = [], []
    for ano, mes in MESES:
        a, b = _inicio(ano, mes), _inicio(ano + mes // 12, mes % 12 + 1)
        df_1s = ler_zip_1s(_zip_mes(serie[(serie["t"] >= a) & (serie["t"] < b)]))
        agregador.adicionar(df_1s)
        ts.append(df_1s.index.to_numpy(dtype="int64"))
        cs.append(df_1s["c"].to_numpy(dtype="float64"))
    t, c = np.concatenate(ts), np.concatenate(cs)
    precos = SeriePrecos(t, c, c, 1000)
    t1 = serie["t"].to_numpy()
    g = serie.groupby(pd.Index(t1 - t1 % 60_000, name="abertura"))
    df_1m = pd.DataFrame(
        {
            "o": g["o"].first(), "h": g["h"].max(), "l": g["l"].min(), "c": g["c"].last(),
            "v": g["v"].sum(), "vb": g["vb"].sum(),
        }
    )  # fmt: skip
    snap = combinar_fs2(
        montar_snapshot_em_blocos(df_1m), features_microestrutura(agregador.resultado())
    )
    r = avaliar_combinacao_v2(
        df_1m, snap, precos, Expiracao.M1, 0.86, treino_meses=1, holdout_meses=0
    )
    m = calcular(r.principal.operacoes, 0.86)
    assert r.principal.dobras == 1
    assert m.wins + m.losses > 1000
    assert m.taxa > 0.9
