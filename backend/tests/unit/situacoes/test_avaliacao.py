import math

import numpy as np
import pandas as pd

from sinais.situacoes.avaliacao import (
    LinhaSituacao,
    avaliar_chave,
    consolidar_familia,
    meses_acima,
    p_duas_proporcoes,
)

from ..analise.sinteticos import T0

M = 60_000
MES = 30 * 24 * 60 * M
MESES = [(T0 + k * MES, T0 + (k + 1) * MES) for k in range(14)]
P_EQ = 1 / 1.86


def _ops(wins: int, losses: int, inicio: int = T0, passo: int = 20 * M) -> pd.DataFrame:
    res = ["WIN"] * wins + ["LOSS"] * losses
    rng = np.random.default_rng(len(res))
    rng.shuffle(res)
    return pd.DataFrame({"decisao": inicio + np.arange(len(res)) * passo, "resultado": res})


def _por_mes(wins_mes: list[int], n_mes: int) -> pd.DataFrame:
    partes = [_ops(w, n_mes - w, inicio=MESES[k][0]) for k, w in enumerate(wins_mes)]
    return pd.concat(partes, ignore_index=True)


def test_meses_acima_exige_minimo_de_operacoes() -> None:
    ops = _por_mes([12] * 10 + [5] * 4, 20)  # 10 meses a 60%, 4 a 25%
    assert meses_acima(ops, P_EQ, MESES, minimo=10) == 10 / 14
    assert meses_acima(ops, P_EQ, MESES, minimo=21) == 0.0
    assert meses_acima(ops.iloc[:0], P_EQ, MESES) == 0.0


def test_duas_proporcoes_unilateral() -> None:
    assert p_duas_proporcoes(600, 1000, 540, 1000) < 0.01
    assert p_duas_proporcoes(540, 1000, 600, 1000) > 0.99
    assert p_duas_proporcoes(0, 0, 10, 20) == 1.0


def _bases(taxa: float, n: int = 2000) -> dict[str, pd.DataFrame]:
    w = int(taxa * n)
    return {"sempre_compra": _ops(w, n - w), "aleatoria": _ops(n // 2, n - n // 2)}


def _linha(
    wins_mes: list[int], n_mes: int, holdout: tuple[int, int], **kw: object
) -> LinhaSituacao:
    padrao: dict[str, object] = {
        "ativo": "BTCUSDT", "variacao": "S1", "espelho": "topo", "expiracao": "15m",
        "camada": "A", "elegivel": True, "baselines": _bases(0.5),
    }  # fmt: skip
    padrao.update(kw)
    return avaliar_chave(
        ops_teste=_por_mes(wins_mes, n_mes),
        ops_holdout=_ops(*holdout),
        meses=MESES,
        payout=0.86,
        **padrao,  # type: ignore[arg-type]
    )


def test_chave_forte_passa_em_tudo() -> None:
    (x,) = consolidar_familia([_linha([26] * 14, 40, (40, 20))])
    assert x.recomendacao == "candidata", x.motivos
    assert x.teste.wins + x.teste.losses == 560


def test_cada_criterio_reprova_sozinho() -> None:
    poucas = _linha([13] * 14, 20, (40, 20))  # 280 operações
    fraca = _linha([22] * 14, 40, (40, 20))  # 55%: Wilson inf. abaixo de 54,76%
    concentrada = _linha([40] * 5 + [18] * 9, 40, (40, 20))
    holdout_ruim = _linha([26] * 14, 40, (20, 40))
    holdout_curto = _linha([26] * 14, 40, (30, 10))
    vence_base = _linha([26] * 14, 40, (40, 20), baselines=_bases(0.70))
    fora = _linha([26] * 14, 40, (40, 20), elegivel=False)
    linhas = consolidar_familia(
        [poucas, fraca, concentrada, holdout_ruim, holdout_curto, vence_base, fora]
    )
    esperado = ["300", "Wilson", "70%", "holdout", "holdout", "simples", "contagem"]
    for x, palavra in zip(linhas, esperado, strict=True):
        assert x.recomendacao != "candidata"
        assert any(palavra in m for m in x.motivos), (palavra, x.motivos)
    assert math.isclose(linhas[-1].pvalor, 1.0)


def test_bh_considera_a_familia_inteira() -> None:
    marginal = _linha([24] * 14, 40, (40, 20))  # 60%: passa sozinha
    (sozinha,) = consolidar_familia([marginal])
    assert sozinha.passou_bh
    ruins = [_linha([21] * 14, 40, (40, 20), variacao=f"X{k}") for k in range(200)]
    linhas = consolidar_familia([marginal, *ruins])
    assert not linhas[0].passou_bh


def test_b_so_adotada_se_supera_a() -> None:
    b_igual = _linha([26] * 14, 40, (40, 20), camada="B", ops_a=_por_mes([26] * 14, 40))
    b_melhor = _linha([30] * 14, 40, (40, 20), camada="B", ops_a=_por_mes([22] * 14, 40))
    x, y = consolidar_familia([b_igual, b_melhor])
    assert x.recomendacao != "candidata" and any("não supera a camada A" in m for m in x.motivos)
    assert y.recomendacao == "candidata", y.motivos
    assert y.p_b_supera_a < 0.05
