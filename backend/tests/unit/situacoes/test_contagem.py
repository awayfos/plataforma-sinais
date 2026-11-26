import pandas as pd

from sinais.core.dominio import Expiracao
from sinais.corretoras.regras import EXNOVA
from sinais.situacoes.contagem import contar, markdown_contagem, tabela_contagem

from ..analise.sinteticos import T0

M = 60_000
R15 = EXNOVA.regras[Expiracao.M15]


def _ev(
    d: int, var: str = "S2", espelho: str = "topo", conflito: bool = False
) -> dict[str, object]:
    return {
        "decisao": d, "variacao": var, "espelho": espelho, "conflito": conflito,
        "direcao": -1 if espelho == "topo" else 1, "ativo": "BTCUSDT",
    }  # fmt: skip


def test_conta_sem_sobreposicao_sem_conflito_e_so_na_janela() -> None:
    ev = pd.DataFrame(
        [
            _ev(T0 + 30 * M),  # vence :45
            _ev(T0 + 33 * M),  # sobreposto
            _ev(T0 + 41 * M),  # fora da janela de 15 min
            _ev(T0 + 46 * M, conflito=True),
            _ev(T0 + 47 * M),  # vence 01:00
            _ev(T0 + 90 * M),  # fora do período
        ]
    )
    assert contar(ev, R15, T0, T0 + 60 * M) == 2


def test_tabela_tem_a_grade_completa_e_marca_elegiveis() -> None:
    ev = pd.DataFrame([_ev(T0 + k * 20 * M) for k in range(500)])
    periodos = {"teste": (T0, T0 + 500 * 20 * M), "holdout": (T0 + 10**12, T0 + 10**12 + 1)}
    tab = tabela_contagem(ev, periodos, {"15m": R15}, ativos=("BTCUSDT", "ETHUSDT"))
    assert len(tab) == 10 * 2 * 2 * 1
    linha = tab[
        (tab["variacao"] == "S2") & (tab["espelho"] == "topo") & (tab["ativo"] == "BTCUSDT")
    ]
    assert linha["teste"].iloc[0] > 300 and bool(linha["elegivel"].iloc[0])
    assert tab["elegivel"].sum() == 1
    texto = markdown_contagem(tab, ["teste", "holdout"])
    assert "| BTCUSDT | S2 | topo | 15m |" in texto
