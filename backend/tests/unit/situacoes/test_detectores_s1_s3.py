import numpy as np
import pandas as pd

from sinais.situacoes.base import montar_base
from sinais.situacoes.detectores import detectar_s1, detectar_s2, detectar_s3
from sinais.situacoes.parametros import ParamS1, ParamS2, ParamS3

from .sinteticos import M, espelhar, minutos


def _decisao(df: pd.DataFrame, i: int) -> int:
    return int(df.index[i]) + M


# ---------- S1: exaustão no topo novo ----------


def _cenario_s1(
    pressao_rompe: float = 0.6, nova_maxima: bool = False, atraso: int = 0
) -> pd.DataFrame:
    n = 270
    c = 100 + 0.01 * np.sin(np.arange(n))
    p = np.full(n, 0.5)
    c[250] = 101.0  # rompimento: máxima nova de 4 h
    h = np.maximum(np.concatenate([[c[0]], c[:-1]]), c) + 0.1
    h[250] = 101.5
    p[250] = pressao_rompe
    c[251:] = 100.9
    p[251], p[252] = 0.40, 0.45  # 2 de 3 com pressão < 50%
    alvo = 253 + atraso
    c[alvo:] = 99.8  # fecha abaixo da mínima do candle do topo (99.9)
    h = np.maximum(np.concatenate([[c[0]], c[:-1]]), c) + 0.1
    h[250] = 101.5
    if nova_maxima:
        h[252] = 101.6
    return minutos(c, h=h, pressao=p)


def test_s1_dispara_no_fechamento_abaixo_da_minima_do_topo() -> None:
    df = _cenario_s1()
    ev = detectar_s1(montar_base(df), ParamS1())
    assert [(e["decisao"], e["espelho"], e["direcao"]) for e in ev] == [
        (_decisao(df, 253), "topo", -1)
    ]
    assert ev[0]["nivel"] == 101.5


def test_s1_nao_dispara_sem_pressao_no_rompimento_com_nova_maxima_ou_tarde() -> None:
    for df in (
        _cenario_s1(pressao_rompe=0.5),
        _cenario_s1(nova_maxima=True),
        _cenario_s1(atraso=9),  # fechamento abaixo 12 min depois do topo
    ):
        assert detectar_s1(montar_base(df), ParamS1()) == []


def test_s1_nao_dispara_com_pressao_indefinida_no_rompimento() -> None:
    df = _cenario_s1()
    df.iloc[250, df.columns.get_loc("v")] = 0.0
    df.iloc[250, df.columns.get_loc("vb")] = 0.0
    assert detectar_s1(montar_base(df), ParamS1()) == []


def test_s1_espelho_no_fundo() -> None:
    df = espelhar(_cenario_s1())
    ev = detectar_s1(montar_base(df), ParamS1())
    assert [(e["decisao"], e["espelho"], e["direcao"]) for e in ev] == [
        (_decisao(df, 253), "fundo", 1)
    ]


# ---------- S2 e S3: regiões com toques em 4 h ----------


def _zigzag(picos: int) -> tuple[np.ndarray, np.ndarray]:
    """20 candles parados em 100 e ``picos`` dentes de serra com máxima 105,1."""
    dente = [101, 102, 103, 104, 105, 104, 103, 102, 101, 100]
    c = np.array([100.0] * 20 + dente * picos, dtype="float64")
    v = np.full(len(c), 10.0)
    return c, v


def _cenario_rompimento(picos: int, volta: bool, forca: bool = True) -> pd.DataFrame:
    c, v = _zigzag(picos)
    b = len(c)
    seguinte = [104.8, 104.5, 104.0] if volta else [106.5, 105.6, 106.0, 106.5]
    c = np.concatenate([c, [102, 103, 104, 105.5], seguinte])
    b += 3
    v = np.concatenate([v, np.full(len(c) - len(v), 10.0)])
    p = np.full(len(c), 0.5)
    if forca:
        v[b], p[b] = 40.0, 0.7
    o = np.concatenate([[c[0]], c[:-1]])
    h = np.maximum(o, c) + 0.1
    lo = np.minimum(o, c) - 0.1
    if not volta:
        lo[b + 1] = 106.0  # afasta-se do nível
        lo[b + 2] = 105.2  # reteste: volta perto do nível e fecha acima
    return minutos(c, h=h, lo=lo, o=o, v=v, pressao=p)


def test_s2_falso_rompimento_de_regiao_com_3_toques() -> None:
    df = _cenario_rompimento(3, volta=True)
    ev = detectar_s2(montar_base(df), ParamS2())
    b = len(df) - 4
    assert [(e["decisao"], e["espelho"], e["direcao"]) for e in ev] == [
        (_decisao(df, b + 1), "topo", -1)
    ]
    assert ev[0]["ordem_toque"] == 4  # 3 toques prévios + o rompimento
    assert ev[0]["min_entre_toques"] == 10.0
    assert abs(ev[0]["nivel"] - 105.1) < 1e-9


def test_s2_nao_dispara_com_2_toques() -> None:
    assert detectar_s2(montar_base(_cenario_rompimento(2, volta=True)), ParamS2()) == []


def test_s2_espelho() -> None:
    df = espelhar(_cenario_rompimento(3, volta=True))
    ev = detectar_s2(montar_base(df), ParamS2())
    assert [(e["espelho"], e["direcao"]) for e in ev] == [("fundo", 1)]


def test_s3_rompimento_com_forca_e_reteste_que_segura() -> None:
    df = _cenario_rompimento(3, volta=False)
    b = len(df) - 5
    ev = detectar_s3(montar_base(df), ParamS3(), "S3")
    assert [(e["decisao"], e["espelho"], e["direcao"], e["variacao"]) for e in ev] == [
        (_decisao(df, b + 2), "topo", 1, "S3")
    ]


def test_s3_sem_volume_ou_pressao_nao_dispara() -> None:
    df = _cenario_rompimento(3, volta=False, forca=False)
    assert detectar_s3(montar_base(df), ParamS3(), "S3") == []


def test_s3b_exige_4_toques() -> None:
    p = ParamS3(toques_min=4)
    assert detectar_s3(montar_base(_cenario_rompimento(3, volta=False)), p, "S3b") == []
    ev = detectar_s3(montar_base(_cenario_rompimento(4, volta=False)), p, "S3b")
    assert [e["variacao"] for e in ev] == ["S3b"] and ev[0]["ordem_toque"] == 5


def test_s3_espelho() -> None:
    df = espelhar(_cenario_rompimento(3, volta=False))
    ev = detectar_s3(montar_base(df), ParamS3(), "S3")
    assert [(e["espelho"], e["direcao"]) for e in ev] == [("fundo", -1)]
