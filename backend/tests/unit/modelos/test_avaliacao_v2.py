from datetime import UTC, datetime

import numpy as np
import pandas as pd
import pytest

from sinais.backtest.metricas import calcular
from sinais.backtest.precos import SeriePrecos
from sinais.core.dominio import Expiracao
from sinais.core.tempo import de_datetime
from sinais.modelos.avaliacao_v2 import ResultadoV2, avaliar_combinacao_v2, dividir_calibracao

M = 60_000
INICIO = de_datetime(datetime(2025, 2, 1, tzinfo=UTC))
DIAS = 28 + 31 + 30 + 31  # fevereiro a maio
N_SEG = DIAS * 86_400
N_MIN = N_SEG // 60


def _dados() -> tuple[pd.DataFrame, SeriePrecos, np.ndarray]:
    rng = np.random.default_rng(0)
    c = np.round(100 + np.cumsum(rng.normal(0, 0.01, N_SEG)), 2)
    t = INICIO + np.arange(N_SEG, dtype="int64") * 1000
    precos = SeriePrecos(t, c, c, 1000)
    por_min = c.reshape(N_MIN, 60)
    idx = pd.Index(INICIO + np.arange(N_MIN) * M, name="abertura")
    df = pd.DataFrame(
        {
            "o": por_min[:, 0],
            "h": por_min.max(axis=1),
            "l": por_min.min(axis=1),
            "c": por_min[:, -1],
            "v": 1.0,
            "vb": 0.5,
        },
        index=idx,
    )
    # direção do minuto seguinte (decisão -> próximo fechamento): a "feature vidente"
    futuro = np.sign(np.r_[por_min[1:, -1], np.nan] - por_min[:, -1])
    return df, precos, futuro


@pytest.fixture(scope="module")
def resultados() -> dict[str, ResultadoV2]:
    df, precos, futuro = _dados()
    rng = np.random.default_rng(1)
    ruido = pd.DataFrame(rng.normal(size=(N_MIN, 3)), index=df.index, columns=list("abc"))
    vidente = ruido.assign(d=np.nan_to_num(futuro) + rng.normal(0, 0.3, N_MIN))

    def avaliar(snap: pd.DataFrame) -> ResultadoV2:
        return avaliar_combinacao_v2(
            df, snap, precos, Expiracao.M1, 0.86, treino_meses=1, holdout_meses=1
        )

    limitado = avaliar_combinacao_v2(
        df, vidente, precos, Expiracao.M1, 0.86, treino_meses=1, holdout_meses=1,
        entrada_max_ms=10_000, tolerancia_atr=0.05,
    )  # fmt: skip
    return {"ruido": avaliar(ruido), "vidente": avaliar(vidente), "limitado": limitado}


def test_sem_vantagem_nao_passa_do_equilibrio(resultados: dict[str, ResultadoV2]) -> None:
    r = resultados["ruido"]
    assert r.principal.dobras == 1
    assert set(r.principal.baselines) == {
        "sempre_compra",
        "sempre_venda",
        "seguir_ultimo",
        "aleatoria",
    }
    m = calcular(r.principal.operacoes, 0.86)
    assert np.isnan(m.wilson_inf) or m.wilson_inf < m.p_equilibrio


def test_sinal_plantado_e_encontrado_no_teste_e_no_holdout(
    resultados: dict[str, ResultadoV2],
) -> None:
    r = resultados["vidente"]
    assert calcular(r.principal.operacoes, 0.86).taxa > 0.6
    assert calcular(r.principal.holdout, 0.86).taxa > 0.6
    assert len(r.limiares_filtro) == r.principal.dobras == 1


def test_operacoes_realistas_em_1s(resultados: dict[str, ResultadoV2]) -> None:
    r = resultados["vidente"]
    for ops in (r.principal.operacoes, r.principal.holdout, r.sem_filtro.operacoes):
        decididas = ops[ops["resultado"].isin(["WIN", "LOSS", "TIE"])]
        assert len(decididas) > 100
        assert (decididas["entrada_t"] % M != 0).mean() > 0.9  # entrada dentro do minuto
        assert (decididas["entrada_t"] >= decididas["decisao"] + 2000).all()
    for ops in r.principal.baselines.values():
        assert (ops["entrada_t"] % M != 0).mean() > 0.9


def test_filtro_so_remove_sinais(resultados: dict[str, ResultadoV2]) -> None:
    for r in resultados.values():
        assert len(r.sem_filtro.sinais_holdout) >= len(r.principal.sinais_holdout)
        assert all(0.0 <= f <= 1.0 for f in r.frac_filtrada)


def test_calibracao_dividida_em_metades_purgadas() -> None:
    h = 60 * M
    calib = (INICIO, INICIO + 30 * 24 * h)
    decisao = np.arange(calib[0] - 5 * h, calib[1] + 5 * h, M)
    rot = pd.DataFrame(
        {"decisao": decisao, "vencimento_t": decisao + 2 * M, "alvo": 1.0, "apertado": 0.0}
    )
    m_iso, m_lim = dividir_calibracao(rot, calib, calib[1], h)
    meio = calib[0] + 15 * 24 * h
    assert not (m_iso & m_lim).any()
    assert (decisao[m_iso] >= calib[0]).all() and (rot["vencimento_t"][m_iso] <= meio - h).all()
    assert (decisao[m_lim] >= meio).all() and (rot["vencimento_t"][m_lim] <= calib[1] - h).all()
    assert abs(int(m_iso.sum()) - int(m_lim.sum())) <= 2


def test_teste_e_holdout_separados_no_filtro(resultados: dict[str, ResultadoV2]) -> None:
    for r in resultados.values():
        assert len(r.limiares_filtro) == len(r.frac_filtrada) == r.principal.dobras
        assert isinstance(r.limiar_filtro_holdout, float)
        assert 0.0 <= r.frac_filtrada_holdout <= 1.0


def test_diagnostico_sem_filtro_tem_baselines_e_avisos_proprios(
    resultados: dict[str, ResultadoV2],
) -> None:
    for r in resultados.values():
        assert r.sem_filtro.baselines is not r.principal.baselines
        assert r.sem_filtro.avisos is not r.principal.avisos
        pd.testing.assert_frame_equal(
            r.sem_filtro.baselines["sempre_compra"], r.principal.baselines["sempre_compra"]
        )
        # aleatória com a frequência de sinais de cada variante
        assert len(r.sem_filtro.baselines["aleatoria"]) >= len(r.principal.baselines["aleatoria"])


def test_entrada_limitada_e_tolerancia_de_preco(resultados: dict[str, ResultadoV2]) -> None:
    r = resultados["limitado"]
    for ops in (r.principal.operacoes, r.principal.holdout, *r.principal.baselines.values()):
        entrou = ops[ops["resultado"].isin(["WIN", "LOSS", "TIE"])]
        assert len(entrou) > 50
        assert ((entrou["entrada_t"] - entrou["decisao"]) <= 10_000).all()
    assert (r.principal.operacoes["resultado"] == "FORA_DA_TOLERANCIA").any()
    assert (r.principal.baselines["sempre_compra"]["resultado"] == "FORA_DA_TOLERANCIA").any()
