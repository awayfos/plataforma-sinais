import pandas as pd

from sinais.situacoes.base import montar_base
from sinais.situacoes.detectores import detectar_s4, detectar_s5
from sinais.situacoes.parametros import ParamS4, ParamS5

from .sinteticos import M, anexar, de_barras, espelhar

# ---------- S4: reteste após BOS no 5m ----------
BARRAS_S4: list[float] = [100, 101, 102, 103, 104, 105, 104, 103, 102, 101, 100]
BARRAS_S4 += [101, 102, 103, 104, 105, 106, 107]  # barra 16 rompe o topo 105,2 (BOS)


def _cenario_s4(engolfo: bool = True, perde_nivel: bool = False) -> pd.DataFrame:
    df = de_barras(BARRAS_S4)
    if perde_nivel:
        df = anexar(df, 107.0, 107.1, 105.0, 105.1)  # fecha abaixo do nível rompido
    df = anexar(df, 107.0, 107.05, 106.4, 106.5)  # candle de baixa
    if not engolfo:  # volta ao nível sem engolfo nem pin bar
        return anexar(df, 106.6, 108.5, 105.25, 107.1)
    return anexar(df, 106.45, 107.2, 105.25, 107.1)  # volta ao nível e engolfa


def test_s4_reteste_com_engolfo_apos_bos() -> None:
    df = _cenario_s4()
    ev = detectar_s4(montar_base(df), ParamS4())
    assert [(e["decisao"], e["espelho"], e["direcao"]) for e in ev] == [
        (int(df.index[-1]) + M, "topo", 1)
    ]
    assert abs(ev[0]["nivel"] - 105.2) < 1e-9


def test_s4_sem_candle_de_rejeicao_ou_com_nivel_perdido_nao_dispara() -> None:
    assert detectar_s4(montar_base(_cenario_s4(engolfo=False)), ParamS4()) == []
    assert detectar_s4(montar_base(_cenario_s4(perde_nivel=True)), ParamS4()) == []


def test_s4_espelho() -> None:
    ev = detectar_s4(montar_base(espelhar(_cenario_s4())), ParamS4())
    assert [(e["espelho"], e["direcao"]) for e in ev] == [("fundo", -1)]


# ---------- S5: CHoCH no 5m após tendência esgotada ----------


def _barras_s5() -> list[float]:
    c = [100.0]
    for _ in range(20):  # tendência forte em dente de serra (sobe 6, desce 3)
        for _ in range(6):
            c.append(c[-1] + 1.0)
        for _ in range(3):
            c.append(c[-1] - 1.0)
    for _ in range(12):  # perna fraca até um topo mais alto (RSI menor: divergência)
        c.append(c[-1] + 0.6)
        c.append(c[-1] - 0.3)
    for _ in range(8):  # queda que rompe o último fundo (CHoCH)
        c.append(c[-1] - 1.5)
    return c


def test_s5_choch_com_adx_alto_e_divergencia() -> None:
    df = de_barras(_barras_s5())
    b = montar_base(df)
    ev = detectar_s5(b, ParamS5())
    assert [(e["decisao"], e["espelho"], e["direcao"]) for e in ev] == [
        (int(b.q5.fech[207]), "topo", -1)
    ]


def test_s5_sem_adx_alto_nao_dispara() -> None:
    assert detectar_s5(montar_base(de_barras(_barras_s5())), ParamS5(adx_min=99.0)) == []


def test_s5_divergencia_velha_nao_conta() -> None:
    p = ParamS5(idade_max_pivo_5m=3)
    assert detectar_s5(montar_base(de_barras(_barras_s5())), p) == []


def test_s5_espelho() -> None:
    ev = detectar_s5(montar_base(espelhar(de_barras(_barras_s5()))), ParamS5())
    assert [(e["espelho"], e["direcao"]) for e in ev] == [("fundo", 1)]
