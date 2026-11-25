import numpy as np
import pandas as pd
import pytest

from sinais.backtest.precos import SeriePrecos
from sinais.core.dominio import Expiracao
from sinais.corretoras.regras import EXNOVA
from sinais.modelos.rotulos import rotular_1s

T0 = 1795575600000
M = 60_000


def _precos(minutos: int = 120, semente: int = 1) -> SeriePrecos:
    rng = np.random.default_rng(semente)
    c = np.round(100 + np.cumsum(rng.normal(0, 0.01, minutos * 60)), 2)
    idx = pd.Index(T0 + np.arange(len(c)) * 1000, name="abertura")
    return SeriePrecos.de_quadro(pd.DataFrame({"o": c, "c": c}, index=idx), 1000)


DECISOES = T0 + np.arange(1, 100) * M


@pytest.mark.parametrize("exp", [Expiracao.M1, Expiracao.M5])
def test_entrada_em_segundo_inteiro_dentro_da_janela(exp: Expiracao) -> None:
    regra = EXNOVA.regras[exp]
    r = rotular_1s(DECISOES, regra, _precos(), semente=3)
    assert (r["entrada_t"] % 1000 == 0).all()
    assert (r["entrada_t"] >= r["decisao"] + 2000).all()
    venc = np.array([regra.vencimento_para(int(d)) for d in DECISOES])
    assert (r["vencimento_t"].to_numpy() == venc).all()
    assert (r["entrada_t"].to_numpy() <= [regra.prazo_compra(int(v)) for v in venc]).all()
    # sorteio de verdade: entradas variam dentro do minuto
    assert r["entrada_t"].sub(r["decisao"]).nunique() > 5


def test_alvo_e_apertado_seguem_a_liquidacao() -> None:
    p = _precos()
    r = rotular_1s(DECISOES, EXNOVA.regras[Expiracao.M1], p, semente=5)
    for linha in r.itertuples():
        pe, pv = p.preco_em(int(linha.entrada_t)), p.preco_em(int(linha.vencimento_t))
        assert pe is not None and pv is not None
        esperado = 1.0 if pv > pe else 0.0 if pv < pe else np.nan
        assert np.isnan(esperado) if np.isnan(linha.alvo) else linha.alvo == esperado
        assert linha.apertado == float(abs(pv - pe) <= 1e-4 * pe)
    assert 0 < r["apertado"].mean() < 1


def test_mesma_semente_mesmo_rotulo() -> None:
    a = rotular_1s(DECISOES, EXNOVA.regras[Expiracao.M1], _precos(), semente=5)
    b = rotular_1s(DECISOES, EXNOVA.regras[Expiracao.M1], _precos(), semente=5)
    pd.testing.assert_frame_equal(a, b)


def test_vencimento_depois_do_fim_dos_dados_vira_nan() -> None:
    p = _precos(minutos=50)
    r = rotular_1s(DECISOES, EXNOVA.regras[Expiracao.M1], p)
    fora = r["vencimento_t"] > T0 + 50 * M
    assert fora.any()
    assert r.loc[fora, "alvo"].isna().all()
    assert r.loc[fora, "apertado"].isna().all()
