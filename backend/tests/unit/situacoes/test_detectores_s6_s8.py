import pandas as pd

from sinais.situacoes.base import montar_base
from sinais.situacoes.detectores import detectar_s6, detectar_s7, detectar_s8
from sinais.situacoes.parametros import ParamS6, ParamS7, ParamS8

from .sinteticos import M, anexar, de_barras, espelhar

OSCILA = [100.0, 102.0, 104.0, 106.0, 104.0, 102.0]


def _ultimo(df: pd.DataFrame) -> int:
    return int(df.index[-1]) + M


# ---------- S6 / S6a: rejeição repetida na máxima de 4 h (15m) ----------


def _cenario_s6(toques: int, pressao: float = 0.4) -> pd.DataFrame:
    barras = OSCILA * 6  # 36 barras de 15m; janela = barras 20..35
    posicoes = [22, 27, 32][:toques]
    maximas = {b: 110.0 - 0.05 * k for k, b in enumerate(posicoes)}
    df = de_barras(barras, por_barra=15, maximas=maximas)
    df = anexar(df, 102.0, 102.5, 101.9, 102.4)
    return anexar(df, 102.4, 109.85, 102.3, 104.0, p=pressao)  # toca a zona e rejeita


def test_s6_quarto_toque_rejeitado() -> None:
    df = _cenario_s6(3)
    b = montar_base(df)
    ev = detectar_s6(b, ParamS6(), "S6")
    assert [(e["decisao"], e["espelho"], e["direcao"], e["ordem_toque"]) for e in ev] == [
        (_ultimo(df), "topo", -1, 4)
    ]
    assert ev[0]["nivel"] == 110.0
    # último toque começou na barra 32: (36 − 32) × 15 min + 2 min até a decisão
    assert ev[0]["min_entre_toques"] == 62.0
    assert detectar_s6(b, ParamS6(toques_previos_min=1, toques_previos_max=2), "S6a") == []


def test_s6a_terceiro_toque() -> None:
    df = _cenario_s6(2)
    p = ParamS6(toques_previos_min=1, toques_previos_max=2)
    ev = detectar_s6(montar_base(df), p, "S6a")
    assert [(e["variacao"], e["ordem_toque"]) for e in ev] == [("S6a", 3)]
    assert detectar_s6(montar_base(df), ParamS6(), "S6") == []


def test_s6_sem_queda_de_pressao_nao_dispara() -> None:
    assert detectar_s6(montar_base(_cenario_s6(3, pressao=0.6)), ParamS6(), "S6") == []


def test_s6_espelho() -> None:
    ev = detectar_s6(montar_base(espelhar(_cenario_s6(3))), ParamS6(), "S6")
    assert [(e["espelho"], e["direcao"]) for e in ev] == [("fundo", 1)]


# ---------- S7: divergência no extremo de 15m ----------


def _cenario_s7(pressao: float = 0.3) -> pd.DataFrame:
    c = [100.0]
    for _ in range(6):
        c += [c[-1] + 1, c[-1] + 2, c[-1] + 3, c[-1] + 4]
        c += [c[-1] - 1, c[-1] - 2, c[-1] - 3]
    for _ in range(14):  # perna fraca até um topo mais alto
        c.append(c[-1] + 0.5)
        c.append(c[-1] - 0.25)
    c += [c[-1] - 0.2]  # 2ª barra depois do topo: confirma o pivô (k = 2)
    df = de_barras(c, por_barra=15)
    for _ in range(2):
        df = anexar(df, 109.45, 109.5, 109.4, 109.45, p=pressao)
    return df


def test_s7_topo_com_divergencia_e_inversao_de_pressao() -> None:
    df = _cenario_s7()
    ev = detectar_s7(montar_base(df), ParamS7())
    assert [(e["decisao"], e["espelho"], e["direcao"]) for e in ev] == [(_ultimo(df), "topo", -1)]
    assert abs(ev[0]["nivel"] - 109.95) < 1e-9


def test_s7_sem_inversao_de_pressao_nao_dispara() -> None:
    assert detectar_s7(montar_base(_cenario_s7(pressao=0.5)), ParamS7()) == []


def test_s7_espelho() -> None:
    ev = detectar_s7(montar_base(espelhar(_cenario_s7())), ParamS7())
    assert [(e["espelho"], e["direcao"]) for e in ev] == [("fundo", 1)]


# ---------- S8: extremo de lateralização ----------


def _cenario_s8(pressao: float = 0.4, adx_max: float = 20.0) -> tuple[pd.DataFrame, ParamS8]:
    df = de_barras(OSCILA * 12, por_barra=15)
    df = anexar(df, 102.0, 102.5, 101.9, 102.4)
    df = anexar(df, 102.4, 105.9, 102.3, 105.0, p=pressao)  # topo da faixa e fecha abaixo
    return df, ParamS8(adx_max=adx_max)


def test_s8_rejeicao_no_topo_da_faixa() -> None:
    df, p = _cenario_s8()
    ev = detectar_s8(montar_base(df), p)
    assert [(e["decisao"], e["espelho"], e["direcao"]) for e in ev] == [(_ultimo(df), "topo", -1)]


def test_s8_com_adx_acima_do_limite_ou_pressao_compradora_nao_dispara() -> None:
    for df, p in (_cenario_s8(adx_max=5.0), _cenario_s8(pressao=0.6)):
        assert detectar_s8(montar_base(df), p) == []


def test_s8_espelho() -> None:
    df, p = _cenario_s8()
    ev = detectar_s8(montar_base(espelhar(df)), p)
    assert [(e["espelho"], e["direcao"]) for e in ev] == [("fundo", 1)]
