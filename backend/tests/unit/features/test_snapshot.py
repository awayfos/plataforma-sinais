import numpy as np
import pandas as pd

from sinais.core.dominio import TempoGrafico
from sinais.features.snapshot import FEATURE_SET_VERSION, agregar_quadro, montar_snapshot

from ..analise.sinteticos import M, passeio, quadro

H = 60 * M
T9 = 1795597200000  # 2026-11-25T09:00:00Z


def test_colunas_com_prefixo_e_versao() -> None:
    s = montar_snapshot(passeio(400))
    assert FEATURE_SET_VERSION == "fs-1"
    prefixos = {"ind_", "pad_", "est_", "vol_", "reg_", "fib_", "pa_", "m5_", "m15_", "h1_"}
    assert all(any(c.startswith(p) for p in prefixos) for c in s.columns)
    assert {"ind_rsi", "m5_ind_rsi", "h1_ind_rsi"} <= set(s.columns)
    assert s.dtypes.map(lambda d: d.kind == "f").all()


def test_agregar_quadro_so_blocos_completos() -> None:
    df = quadro(np.arange(12, dtype="float64"), t0=T9)
    a = agregar_quadro(df.drop(df.index[7]), TempoGrafico.M5)
    assert a.index.tolist() == [T9]
    assert a.loc[T9, "c"] == 4.0
    assert a.loc[T9, "v"] == 50.0


def test_contexto_usa_candle_fechado() -> None:
    df = quadro(100 + np.sin(np.arange(150) / 7), t0=T9 - 60 * M)
    s = montar_snapshot(df, contextos=(TempoGrafico.H1,))
    assert s.loc[T9 + 7 * M, "h1_idade_ctx"] == 8
    assert s.loc[T9 + 59 * M, "h1_idade_ctx"] == 0
    assert s.loc[T9 + 58 * M, "h1_idade_ctx"] == 59
    assert not any(c.endswith("abertura_ctx") for c in s.columns)


def test_contexto_vencido_por_lacuna_vira_nan() -> None:
    df = quadro(100 + np.sin(np.arange(180) / 7), t0=T9 - 60 * M)
    df = df.drop(T9 + 30 * M)
    s = montar_snapshot(df, contextos=(TempoGrafico.H1,))
    assert not np.isnan(s.loc[T9 + 7 * M, "h1_pad_doji"])
    assert s.loc[T9 + H + 7 * M, "h1_idade_ctx"] == 68
    assert np.isnan(s.loc[T9 + H + 7 * M, "h1_pad_doji"])


def test_quadro_curto_sem_excecao() -> None:
    s = montar_snapshot(quadro([1.0, 2, 3, 4, 5]))
    assert len(s) == 5
    assert s["ind_rsi"].isna().all()
    assert s["h1_ind_rsi"].isna().all()


def test_snapshot_preserva_indice() -> None:
    df = passeio(300)
    pd.testing.assert_index_equal(montar_snapshot(df).index, df.index)
