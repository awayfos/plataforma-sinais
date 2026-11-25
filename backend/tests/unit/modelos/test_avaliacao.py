from datetime import UTC, datetime

import numpy as np
import pandas as pd

from sinais.core.dominio import Expiracao
from sinais.core.tempo import de_datetime
from sinais.modelos.avaliacao import avaliar_combinacao, mascara_periodo, sinais_do_modelo

M = 60_000
H = 60 * M


def test_limiar_aguardar_no_meio() -> None:
    s = sinais_do_modelo(np.array([1, 2, 3, 4]), np.array([0.56, 0.50, 0.44, 0.55]), 0.555)
    assert s["decisao"].tolist() == [1, 3]
    assert s["direcao"].tolist() == [1, -1]


def test_mascara_remove_rotulo_no_embargo() -> None:
    ate = 10 * H
    rot = pd.DataFrame(
        {
            "decisao": [ate - 3 * H, ate - 70 * M, ate - 30 * M],
            "vencimento_t": [ate - 3 * H + M, ate - 70 * M + 15 * M, ate - 30 * M + M],
            "alvo": [1.0, 0.0, 1.0],
        }
    )
    m = mascara_periodo(rot, inicio=0, fim=ate, seguinte=ate, embargo_ms=H)
    assert m.tolist() == [True, False, False]


def test_ponta_a_ponta_sem_vantagem_nao_passa() -> None:
    inicio = de_datetime(datetime(2025, 1, 1, tzinfo=UTC))
    n = 4 * 31 * 24 * 60
    rng = np.random.default_rng(0)
    c = 100 + np.cumsum(rng.normal(0, 0.05, n))
    o = np.concatenate([[c[0]], c[:-1]])
    idx = pd.Index(inicio + np.arange(n) * M, name="abertura")
    df = pd.DataFrame(
        {
            "o": o,
            "h": np.maximum(o, c) + 0.01,
            "l": np.minimum(o, c) - 0.01,
            "c": c,
            "v": 1.0,
            "vb": 0.5,
        },
        index=idx,
    )
    snap = pd.DataFrame(rng.normal(size=(n, 4)), index=idx, columns=list("abcd"))
    r = avaliar_combinacao(
        df, snap, Expiracao.M15, payout=0.85, treino_meses=1, calibracao_meses=1, holdout_meses=1
    )
    assert r.dobras >= 1
    assert set(r.baselines) == {"sempre_compra", "sempre_venda", "seguir_ultimo", "aleatoria"}
    from sinais.backtest.metricas import calcular

    m = calcular(r.operacoes, 0.85)
    # sem vantagem real: o limite inferior de Wilson não pode passar do equilíbrio
    assert np.isnan(m.wilson_inf) or m.wilson_inf < m.p_equilibrio
    assert r.ece_medio < 0.05
