import numpy as np
import pandas as pd

from sinais.situacoes.parametros import LIMIARES_B
from sinais.situacoes.periodos import periodos_descoberta
from sinais.situacoes.qualificadora import avaliar_b, escolher_limiar

P = periodos_descoberta("2026-10", 24)
P_EQ = 1 / 1.86


def _dados(n: int, semente: int = 0) -> tuple[pd.DataFrame, list[str]]:
    """Eventos espalhados no período; a situação vence 75% das vezes quando ``ctx > 1`` e 50% no
    resto (sinal plantado só no contexto)."""
    rng = np.random.default_rng(semente)
    d = np.sort(rng.integers(P.inicio, P.fim - 3_600_000, n)) // 60_000 * 60_000
    ctx = rng.normal(0, 1, n)
    ruido = rng.normal(0, 1, (n, 3))
    vence = rng.random(n) < np.where(ctx > 1, 0.75, 0.5)
    df = pd.DataFrame(
        {
            "decisao": d,
            "vencimento_t": d + 900_000,
            "resultado": np.where(vence, "WIN", "LOSS"),
            "ctx": ctx,
            "r0": ruido[:, 0],
            "r1": ruido[:, 1],
            "r2": ruido[:, 2],
        }
    )
    return df, ["ctx", "r0", "r1", "r2"]


def test_limiar_escolhido_pelo_maior_wilson_com_minimo() -> None:
    p = np.array([0.56] * 100 + [0.60] * 40)
    y = np.array([1] * 52 + [0] * 48 + [1] * 32 + [0] * 8)
    assert escolher_limiar(p, y, P_EQ) == P_EQ + LIMIARES_B[1]  # p ≥ 0,5676: só os 40 de 80%
    assert escolher_limiar(p[:100], y[:100], P_EQ) == P_EQ + LIMIARES_B[0]
    assert escolher_limiar(p[:10], y[:10], P_EQ) == P_EQ + LIMIARES_B[0]  # nenhum com ≥ 30


def test_b_libera_os_eventos_com_sinal_plantado() -> None:
    dados, colunas = _dados(40_000)
    r = avaliar_b(dados, colunas, P, P_EQ)
    assert r is not None
    teste = dados[r.liberado_teste]
    assert len(teste) > 300
    assert (teste["ctx"] > 1).mean() > 0.7
    taxa_b = (teste["resultado"] == "WIN").mean()
    m_te = (dados["decisao"] >= P.teste[0]) & (dados["decisao"] < P.teste[1])
    taxa_a = (dados.loc[m_te, "resultado"] == "WIN").mean()
    assert taxa_b > taxa_a + 0.1
    assert r.liberado_holdout.sum() > 50
    assert len(r.limiares) == 14
    assert not (r.liberado_teste & r.liberado_holdout).any()


def test_b_nao_tentada_com_menos_de_1000_linhas_de_treino() -> None:
    dados, colunas = _dados(3_000)
    assert avaliar_b(dados, colunas, P, P_EQ) is None


def test_coluna_toda_vazia_nao_quebra_o_treino() -> None:
    """Achado da 1ª rodada real: em S1 ``ordem_toque`` é sempre NaN e o HGB falha no binning."""
    from sinais.situacoes.qualificadora import treinar_qualificadora

    rng = np.random.default_rng(1)
    x = np.column_stack([rng.normal(0, 1, 2000), np.full(2000, np.nan)]).astype("float32")
    y = (rng.random(2000) < 0.5).astype("int64")
    p = treinar_qualificadora(x, y).probabilidade(x)
    assert p.shape == (2000,) and np.isfinite(p).all()
