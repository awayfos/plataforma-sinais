import math

import pandas as pd

from sinais.analise.estrutura import estrutura, pivos


def df(h: list[float], l: list[float], c: list[float]) -> pd.DataFrame:  # noqa: E741
    o = [c[0], *c[:-1]]
    return pd.DataFrame({"o": o, "h": h, "l": l, "c": c, "v": 1.0, "vb": 0.5})


ALTA = df(
    [1, 3, 2, 4, 3, 5, 4, 6.5],
    [0, 2, 1, 3, 2, 4, 3, 4],
    [0.5, 2.5, 1.5, 3.5, 2.5, 4.5, 3.5, 6],
)
BAIXA_VIRA = df(
    [10, 8, 9, 7, 8, 6, 7, 9.5],
    [9, 7, 8, 6, 7, 5, 6, 6.5],
    [9.5, 7.5, 8.5, 6.5, 7.5, 5.5, 6.5, 9],
)


def test_pivo_so_confirma_apos_k() -> None:
    p = pivos(ALTA, k=1)
    assert math.isnan(p["topo"][1])
    assert p["topo"][2] == 3
    assert p["fundo"][3] == 1
    assert p["topo"].dropna().tolist() == [3, 4, 5]
    assert p["fundo"].dropna().tolist() == [1, 2, 3]


def test_pivo_k3_nao_aparece_sem_3_candles_a_direita() -> None:
    h: list[float] = [1, 2, 3, 10, 3, 2]
    p = pivos(df(h, [x - 1 for x in h], [x - 0.5 for x in h]), k=3)
    assert p["topo"].isna().all()


def test_hh_hl_tendencia_alta() -> None:
    e = estrutura(ALTA, k=1)
    assert e["rotulo_topo"][4] == 1
    assert e["rotulo_fundo"][5] == 1
    assert e["tendencia"][5] == 1
    assert e["tendencia"][2] == 0


def test_bos_alta() -> None:
    e = estrutura(ALTA, k=1)
    # cada fechamento acima do último topo confirmado é rompimento a favor (BOS)
    assert e["bos"].tolist() == [0, 0, 0, 1, 0, 1, 0, 1]
    assert e["choch"].eq(0).all()


def test_choch_virada() -> None:
    e = estrutura(BAIXA_VIRA, k=1)
    assert e["tendencia"][6] == -1
    assert e["choch"][7] == 1
    assert e["bos"][7] == 0
