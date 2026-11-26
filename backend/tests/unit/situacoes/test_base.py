import numpy as np

from sinais.situacoes.base import montar_base

from .sinteticos import M, minutos


def test_mapa_para_ultimo_bloco_de_15m_fechado() -> None:
    df = minutos(np.linspace(100, 110, 60))
    b = montar_base(df)
    # linha 14 fecha às 00:15 → bloco 00:00 já fechado; linha 13 fecha às 00:14 → nenhum
    assert b.idx15[13] == -1
    assert b.idx15[14] == 0
    assert b.q15.t[b.idx15[14]] == df.index[0]
    assert b.idx15[29] == 1
    assert b.idx5[4] == 0 and b.idx5[3] == -1
    assert (b.decisao == df.index.to_numpy() + M).all()


def test_bloco_com_minuto_faltando_nao_existe_e_contexto_vencido_vira_menos_um() -> None:
    df = minutos(np.linspace(100, 110, 90)).drop(index=[minutos([1.0]).index[0] + 20 * M])
    b = montar_base(df)
    assert list(b.q15.t) == [int(df.index[0]) + k * 15 * M for k in (0, 2, 3, 4, 5)]
    # minuto 29 (posição 28 após a remoção) fecha às 00:30: bloco 00:15 incompleto; o de
    # 00:00 tem mais de 15 min de idade → −1
    pos = int(np.searchsorted(df.index, int(df.index[0]) + 29 * M))
    assert b.idx15[pos] == -1


def test_pressao_nan_com_volume_zero() -> None:
    df = minutos([100.0, 101.0, 102.0], v=[10.0, 0.0, 5.0], pressao=0.6)
    b = montar_base(df)
    assert np.isnan(b.pressao[1])
    assert b.pressao[0] == 0.6
