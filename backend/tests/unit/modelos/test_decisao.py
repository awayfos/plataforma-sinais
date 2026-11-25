import pandas as pd

from sinais.core.dominio import Expiracao
from sinais.modelos.avaliacao import ResultadoCombinacao
from sinais.modelos.decisao import consolidar, gerar_markdown_decisao

JAN = 1735689600000  # 2025-01-01
MES = 31 * 86_400_000


def ops(wins: int, losses: int, meses: int = 3) -> pd.DataFrame:
    res = ["WIN"] * wins + ["LOSS"] * losses
    t = [JAN + (i % meses) * MES + i * 1000 for i in range(len(res))]
    return pd.DataFrame({"resultado": res, "entrada_t": t})


def resultado(w: int, lo: int, hw: int, hl: int, base_w: int = 500) -> ResultadoCombinacao:
    return ResultadoCombinacao(
        expiracao=Expiracao.M15,
        operacoes=ops(w, lo),
        holdout=ops(hw, hl, meses=1),
        baselines={"sempre_compra": ops(base_w, 1000 - base_w)},
        ece_medio=0.01,
        dobras=3,
        meses_testados=3,
    )


def test_aprova_so_com_vantagem_forte_e_holdout() -> None:
    linhas = consolidar(
        {
            ("BTCUSDT", Expiracao.M15): resultado(700, 300, 70, 30),
            ("ETHUSDT", Expiracao.M15): resultado(520, 480, 52, 48),
        },
        payout=0.85,
    )
    por_ativo = {x.ativo: x for x in linhas}
    assert por_ativo["BTCUSDT"].recomendacao == "ligar"
    assert por_ativo["ETHUSDT"].recomendacao == "não ligar"
    assert "Wilson" in por_ativo["ETHUSDT"].motivo


def test_holdout_ruim_reprova() -> None:
    [linha] = consolidar({("BTCUSDT", Expiracao.M15): resultado(700, 300, 40, 60)}, 0.85)
    assert linha.recomendacao == "não ligar"
    assert "holdout" in linha.motivo


def test_markdown_tem_hipoteses_e_tabela() -> None:
    linhas = consolidar({("BTCUSDT", Expiracao.M15): resultado(520, 480, 52, 48)}, 0.85)
    texto = gerar_markdown_decisao(linhas, {"payout": "0.85 (hipotético)"})
    assert "0.85 (hipotético)" in texto
    assert "| BTCUSDT | 15m |" in texto


def test_holdout_pequeno_reprova() -> None:
    [linha] = consolidar({("BTCUSDT", Expiracao.M15): resultado(700, 300, 3, 1)}, 0.85)
    assert linha.recomendacao == "não ligar"
    assert "holdout" in linha.motivo


def test_meses_sem_operacao_contam_como_abaixo() -> None:
    r = resultado(700, 300, 70, 30)
    r.meses_testados = 14
    [linha] = consolidar({("BTCUSDT", Expiracao.M15): r}, 0.85)
    assert linha.meses_acima < 0.7
    assert linha.recomendacao == "não ligar"
