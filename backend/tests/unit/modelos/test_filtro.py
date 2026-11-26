import math

import numpy as np
import pytest

from sinais.modelos.filtro import escolher_limiar_filtro, treinar_filtro
from sinais.modelos.treino import ErroTreino

LIMIAR = 0.5476


def _caso(n: int, semente: int = 0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Todos os sinais compram; com p_ap alto (metade de cima) o resultado é moeda, com p_ap
    baixo acerta 65%."""
    rng = np.random.default_rng(semente)
    p_ap = rng.random(n)
    p_dir = np.full(n, 0.6)
    acerto = np.where(p_ap > 0.5, 0.5, 0.65)
    alvo = (rng.random(n) < acerto).astype("float64")
    return p_dir, p_ap, alvo


def test_escolhe_quantil_quando_apertados_previstos_sao_moeda() -> None:
    p_dir, p_ap, alvo = _caso(4000)
    limiar = escolher_limiar_filtro(p_dir, p_ap, alvo, LIMIAR)
    assert math.isfinite(limiar)
    assert np.isclose(limiar, np.quantile(p_ap, 0.5))


def test_filtro_que_atrapalha_fica_de_fora() -> None:
    p_dir, p_ap, alvo = _caso(4000)
    # inverte: agora os "apertados previstos" são os que acertam mais
    assert escolher_limiar_filtro(p_dir, 1 - p_ap, alvo, LIMIAR) == math.inf


def test_poucos_casos_fica_sem_filtro() -> None:
    p_dir, p_ap, alvo = _caso(90)
    assert escolher_limiar_filtro(p_dir, p_ap, alvo, LIMIAR) == math.inf


def test_venda_conta_acerto_quando_cai_e_ignora_aguardar_e_empate() -> None:
    p_dir = np.array([0.40] * 200 + [0.50] * 200)
    alvo = np.array([0.0] * 120 + [1.0] * 70 + [np.nan] * 10 + [1.0] * 200)
    p_ap = np.zeros(400)
    # só as 190 vendas decididas contam: sem quantil distinto, sem filtro
    assert escolher_limiar_filtro(p_dir, p_ap, alvo, LIMIAR, n_minimo=100) == math.inf


def test_filtro_aprende_volatilidade_baixa() -> None:
    rng = np.random.default_rng(2)
    x = rng.normal(size=(3000, 3))
    apertado = (x[:, 0] < -0.3).astype("float64")
    f = treinar_filtro(x, apertado)
    p = f.probabilidade(np.array([[-2.0, 0, 0], [2.0, 0, 0]]))
    assert p[0] > 0.8 and p[1] < 0.2


def test_filtro_com_uma_classe_recusa() -> None:
    with pytest.raises(ErroTreino):
        treinar_filtro(np.zeros((10, 2)), np.zeros(10))
