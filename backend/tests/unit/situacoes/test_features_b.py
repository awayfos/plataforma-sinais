import numpy as np
import pandas as pd

from sinais.features.fs2 import montar_snapshot_fs2
from sinais.features.microestrutura import agregar_segundos, features_microestrutura
from sinais.situacoes.features_b import COLUNAS_CONTEXTO, matriz_b, snapshot_fs2_nas_linhas

from ..features.sinteticos_1s import para_1m, passeio_1s

M = 60_000


def test_snapshot_nas_linhas_igual_ao_completo_com_varios_blocos() -> None:
    s1 = passeio_1s(400, semente=2)
    m1 = para_1m(s1)
    completo = montar_snapshot_fs2(m1, s1)
    linhas = m1.index[[50, 199, 200, 201, 399]]
    micro = features_microestrutura(agregar_segundos(s1))
    parcial = snapshot_fs2_nas_linhas(m1, micro, linhas, bloco=200)
    pd.testing.assert_frame_equal(
        parcial, completo.loc[linhas].astype("float32"), check_exact=False, rtol=1e-5
    )


def test_matriz_b_junta_contexto_e_identificadores() -> None:
    s1 = passeio_1s(100, semente=3)
    m1 = para_1m(s1)
    snap = montar_snapshot_fs2(m1, s1)
    ev = pd.DataFrame(
        {
            "decisao": [int(m1.index[10]) + M, int(m1.index[20]) + M],
            "vencimento_t": [int(m1.index[10]) + 16 * M, int(m1.index[20]) + 16 * M],
            "espelho": ["topo", "fundo"],
            "ativo": ["BTCUSDT", "ETHUSDT"],
            "direcao": [-1, 1],
            **{c: [1.0, 2.0] for c in ("ordem_toque", "min_entre_toques", "dist_sr_atr")},
            "queda_pressao": [0.1, 0.2],
            "confluencias": [0, 3],
        }
    )
    x, colunas = matriz_b(ev, snap)
    assert set(COLUNAS_CONTEXTO) <= set(colunas)
    assert x["espelho_id"].tolist() == [1.0, 0.0] and x["ativo_id"].tolist() == [0.0, 1.0]
    assert x["tempo_restante_s"].tolist() == [900.0, 900.0]
    esperado = snap["ind_rsi"].iloc[[10, 20]].to_numpy()
    assert np.allclose(x["ind_rsi"].to_numpy(), esperado, equal_nan=True)
