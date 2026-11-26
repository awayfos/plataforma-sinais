import numpy as np
import pandas as pd

from sinais.backtest.precos import SeriePrecos
from sinais.situacoes.confirmacao import (
    avaliar_confirmacao,
    consolidar_confirmacao,
    meses_fechados,
)
from sinais.situacoes.relatorio import REGRAS

from ..analise.sinteticos import T0
from ..features.sinteticos_1s import para_1m, passeio_1s

H = 3_600_000


def test_meses_fechados_desde_2026_11() -> None:
    assert meses_fechados("2026-11", "2026-11-26") == []
    assert meses_fechados("2026-11", "2026-12-01") == ["2026-11"]
    assert meses_fechados("2026-11", "2027-02-15") == ["2026-11", "2026-12", "2027-01"]


def _dados() -> tuple[pd.DataFrame, SeriePrecos]:
    s1 = passeio_1s(48 * 60, semente=4)
    s1[["o", "h", "l", "c"]] = s1[["o", "h", "l", "c"]] * 10
    return para_1m(s1), SeriePrecos(
        s1.index.to_numpy(), s1["c"].to_numpy(), s1["c"].to_numpy(), 1000
    )


def test_confirmacao_acumulada_nao_muda_o_passado_e_gera_registros() -> None:
    m1, precos = _dados()
    candidatas = [
        {"ativo": "BTCUSDT", "variacao": v, "espelho": e, "expiracao": "15m", "camada": "A"}
        for v in ("S1", "S2", "S8") for e in ("topo", "fundo")
    ]  # fmt: skip
    inicio = T0 + 12 * H  # "meses novos" começam aqui; antes é só aquecimento
    curto = avaliar_confirmacao("BTCUSDT", m1.iloc[: 30 * 60], precos, candidatas, REGRAS, inicio)
    longo = avaliar_confirmacao("BTCUSDT", m1, precos, candidatas, REGRAS, inicio)
    assert {k for k in curto.registros} == {k for k in longo.registros}
    for k, regs in curto.registros.items():
        # registros liquidados até o fim do trecho curto continuam iguais no acumulado
        fim = int(m1.index[30 * 60 - 1]) - H
        antigos = [r for r in regs if r.vencimento_t < fim]
        assert antigos == [r for r in longo.registros[k] if r.vencimento_t < fim]
        assert all(r.entrada_t >= inicio for r in regs)
    regs = [r for v in longo.registros.values() for r in v]
    assert regs and {r.resultado for r in regs} <= {"WIN", "LOSS", "EMPATE"}
    linhas = consolidar_confirmacao([longo], 0.86)
    assert len(linhas) == len(candidatas)
    assert all(x.status in ("em andamento", "confirmada", "não confirmada") for x in linhas)
    assert all(x.status == "em andamento" for x in linhas if x.n < 100)


def test_camada_b_na_confirmacao_e_declarada_como_pendente() -> None:
    m1, precos = _dados()
    cand = [{"ativo": "BTCUSDT", "variacao": "S2", "espelho": "topo", "expiracao": "15m",
             "camada": "B"}]  # fmt: skip
    r = avaliar_confirmacao("BTCUSDT", m1, precos, cand, REGRAS, T0 + 12 * H)
    (x,) = consolidar_confirmacao([r], 0.86)
    assert x.status == "pendente (camada B)"
    assert np.isnan(x.taxa)


def test_markdown_da_confirmacao_mostra_status_e_sinais() -> None:
    from sinais.situacoes.confirmacao import markdown_confirmacao

    m1, precos = _dados()
    cand = [{"ativo": "BTCUSDT", "variacao": "S2", "espelho": e, "expiracao": "15m",
             "camada": "A"} for e in ("topo", "fundo")]  # fmt: skip
    r = avaliar_confirmacao("BTCUSDT", m1, precos, cand, REGRAS, T0 + 12 * H)
    texto = markdown_confirmacao(consolidar_confirmacao([r], 0.86), [r], ["2026-11"])
    assert "| BTCUSDT | S2 | topo | 15m | A |" in texto
    assert "· BTCUSDT · 15 min |" in texto
    assert "em andamento" in texto
