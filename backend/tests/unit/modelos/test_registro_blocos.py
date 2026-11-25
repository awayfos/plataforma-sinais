from pathlib import Path

import numpy as np
import pytest

from sinais.features.snapshot import JANELA_AO_VIVO_1M, montar_snapshot
from sinais.modelos.blocos import montar_snapshot_em_blocos
from sinais.modelos.registro import ErroPromocao, Registro

from ..analise.sinteticos import passeio


def test_blocos_reproduzem_o_snapshot_inteiro() -> None:
    df = passeio(JANELA_AO_VIVO_1M * 2 + 4000, semente=9)
    inteiro = montar_snapshot(df).iloc[-3000:]
    blocos = montar_snapshot_em_blocos(df, bloco=JANELA_AO_VIVO_1M + 3000).iloc[-3000:]
    assert blocos.dtypes.map(lambda d: d == np.float32).all()
    a, b = inteiro.to_numpy(dtype="float64"), blocos.to_numpy(dtype="float64")
    assert np.isclose(a, b, rtol=1e-3, atol=1e-5, equal_nan=True).all()
    assert list(blocos.index) == list(inteiro.index)


def test_registro_promove_so_se_aprovado_e_melhor(tmp_path: Path) -> None:
    r = Registro(tmp_path)
    r.salvar("BTCUSDT", "15m", "v1", {"modelo": 1}, {"aprovada": True, "taxa": 0.56})
    r.promover("BTCUSDT", "15m", "v1")
    assert (r.campeao("BTCUSDT", "15m") or {})["versao"] == "v1"
    r.salvar("BTCUSDT", "15m", "v2", {"modelo": 2}, {"aprovada": True, "taxa": 0.55})
    with pytest.raises(ErroPromocao):
        r.promover("BTCUSDT", "15m", "v2")
    r.salvar("BTCUSDT", "15m", "v3", {"modelo": 3}, {"aprovada": False, "taxa": 0.60})
    with pytest.raises(ErroPromocao):
        r.promover("BTCUSDT", "15m", "v3")
    assert (r.campeao("BTCUSDT", "15m") or {})["versao"] == "v1"
    assert r.carregar("BTCUSDT", "15m", "v1") == {"modelo": 1}


def test_sem_campeao_none(tmp_path: Path) -> None:
    assert Registro(tmp_path).campeao("ETHUSDT", "1m") is None
