import numpy as np
import pandas as pd

from sinais.situacoes.motor import detectar_todas, marcar_confluencia_e_conflito
from sinais.situacoes.parametros import VARIACOES

from .sinteticos import M, espelhar, passeio

SERIE = passeio(12_000, semente=8)  # semente com ao menos um S6 (raro em passeio)
TODOS = detectar_todas(SERIE)


def _ev(d: int, var: str, direcao: int, espelho: str = "topo") -> dict[str, object]:
    return {"decisao": d, "variacao": var, "direcao": direcao, "espelho": espelho}


def test_conflito_no_mesmo_minuto_e_confluencia_em_15_min() -> None:
    ev = pd.DataFrame(
        [
            _ev(0, "S1", -1),
            _ev(5 * M, "S6", -1),
            _ev(5 * M, "S3", 1),  # direção oposta no mesmo minuto: conflito para os dois
            _ev(14 * M, "S8", -1),
            _ev(30 * M, "S7", -1),
        ]
    )
    saida = marcar_confluencia_e_conflito(ev)
    assert saida["conflito"].tolist() == [False, True, True, False, False]
    # S8 em 14 min: S1 (0) e S6 (5 min) concordam dentro de (−1 min, 14 min]
    assert saida["confluencias"].tolist() == [0, 1, 0, 2, 0]


def test_esquema_e_ordem() -> None:
    assert TODOS["decisao"].is_monotonic_increasing
    assert set(TODOS["variacao"]) <= {v.nome for v in VARIACOES}
    assert TODOS["direcao"].isin([-1, 1]).all()
    assert TODOS["dist_sr_atr"].notna().mean() > 0.9
    assert TODOS["queda_pressao"].notna().mean() > 0.9


def test_cobre_todas_as_variacoes() -> None:
    assert set(TODOS["variacao"]) == {v.nome for v in VARIACOES}


def test_espelho_do_preco_espelha_as_situacoes() -> None:
    refletido = detectar_todas(espelhar(SERIE))
    troca = {"topo": "fundo", "fundo": "topo"}
    a = set(
        zip(TODOS["decisao"], TODOS["variacao"], TODOS["espelho"], TODOS["direcao"], strict=True)
    )
    b = {
        (d, v, troca[e], -x)
        for d, v, e, x in zip(
            refletido["decisao"], refletido["variacao"], refletido["espelho"],
            refletido["direcao"], strict=True,
        )
    }  # fmt: skip
    assert a == b
    assert np.allclose(
        TODOS["queda_pressao"].to_numpy(), refletido["queda_pressao"].to_numpy(), equal_nan=True
    )
