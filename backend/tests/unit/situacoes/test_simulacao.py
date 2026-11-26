import numpy as np
import pandas as pd

from sinais.backtest.precos import SeriePrecos
from sinais.backtest.simulador import simular
from sinais.core.dominio import Expiracao
from sinais.corretoras.regras import EXNOVA
from sinais.situacoes.parametros import Execucao
from sinais.situacoes.simulacao import deslocamento_entrada, simular_eventos

from ..analise.sinteticos import T0

M = 60_000
R15 = EXNOVA.regras[Expiracao.M15]
R5 = EXNOVA.regras[Expiracao.M5]


def _precos(segundos: int = 4 * 3600, semente: int = 1, t0: int = T0) -> SeriePrecos:
    rng = np.random.default_rng(semente)
    t = t0 + np.arange(segundos) * 1000
    c = 100 + np.cumsum(rng.normal(0, 0.01, segundos))
    return SeriePrecos(t, c, c, 1000)


def _eventos(decisoes: list[int], direcao: int = 1) -> pd.DataFrame:
    return pd.DataFrame({"decisao": decisoes, "direcao": [direcao] * len(decisoes)})


def _atr(decisoes: list[int], valor: float = 10.0) -> pd.Series:
    return pd.Series(valor, index=pd.Index(decisoes, dtype="int64"))


def test_deslocamento_entre_2_e_10_s_e_independente_do_lote() -> None:
    d = T0 + np.arange(5000) * M
    s = deslocamento_entrada(d, 7)
    assert s.min() == 2 and s.max() == 10
    assert len(np.unique(s)) == 9
    assert (deslocamento_entrada(d[1234:1300], 7) == s[1234:1300]).all()
    assert not (deslocamento_entrada(d, 8) == s).all()


def test_janela_de_compra_de_15_min() -> None:
    # T0 é hora cheia: decisão às :30 → vence às :45 (15 min); às :40 → só 01:00 (20 min)
    d = [T0 + 30 * M, T0 + 40 * M, T0 + 44 * M, T0 + 46 * M]
    ops = simular_eventos(_eventos(d), _precos(), R15, _atr(d), sem_sobreposicao=False)
    assert ops["resultado"].tolist()[1:3] == ["FORA_DA_JANELA", "FORA_DA_JANELA"]
    assert ops["vencimento_t"].iloc[0] == T0 + 45 * M
    assert 890 <= ops["tempo_restante_s"].iloc[0] <= 898
    assert ops["resultado"].iloc[0] in ("WIN", "LOSS", "TIE")
    assert ops["vencimento_t"].iloc[3] == T0 + 60 * M


def test_um_sinal_ativo_por_vencimento() -> None:
    d = [T0 + 30 * M, T0 + 31 * M, T0 + 45 * M]
    ops = simular_eventos(_eventos(d), _precos(), R15, _atr(d))
    assert ops["resultado"].iloc[1] == "IGNORADO_ATIVO"
    assert ops["resultado"].iloc[2] in ("WIN", "LOSS", "TIE")


def test_tolerancia_de_preco_recusa_entrada() -> None:
    d = [T0 + 30 * M]
    ops = simular_eventos(_eventos(d), _precos(), R15, _atr(d, 1e-9))
    assert ops["resultado"].tolist() == ["FORA_DA_TOLERANCIA"]
    # recusa não bloqueia o próximo sinal
    d2 = [T0 + 30 * M, T0 + 31 * M]
    atr = pd.Series([1e-9, 10.0], index=pd.Index(d2, dtype="int64"))
    assert simular_eventos(_eventos(d2), _precos(), R15, atr)["resultado"].iloc[1] != (
        "IGNORADO_ATIVO"
    )


def test_vencimento_depois_do_fim_dos_dados_e_sem_dado() -> None:
    d = [T0 + 4 * 3600_000 - 10 * M]  # vence às T0 + 4 h; os segundos acabam 1 min antes
    ops = simular_eventos(_eventos(d), _precos(4 * 3600 - 60), R15, _atr(d))
    assert ops["resultado"].tolist() == ["SEM_DADO"]


def test_empate_e_direcao() -> None:
    t = T0 + np.arange(3600) * 1000
    plano = SeriePrecos(t, np.full(3600, 50.0), np.full(3600, 50.0), 1000)
    d = [T0 + 30 * M]
    assert simular_eventos(_eventos(d), plano, R15, _atr(d))["resultado"].tolist() == ["TIE"]
    p = _precos()
    compra = simular_eventos(_eventos(d, 1), p, R15, _atr(d))
    venda = simular_eventos(_eventos(d, -1), p, R15, _atr(d))
    assert {compra["resultado"].iloc[0], venda["resultado"].iloc[0]} == {"WIN", "LOSS"}


def test_lote_mes_a_mes_igual_a_serie_inteira() -> None:
    p = _precos(6 * 3600)
    d = [int(x) for x in T0 + np.arange(0, 330, 7) * M]
    inteiro = simular_eventos(_eventos(d), p, R5, _atr(d))
    partes = pd.concat(
        [simular_eventos(_eventos(x), p, R5, _atr(x)) for x in (d[:20], d[20:])],
        ignore_index=True,
    )
    decididos = inteiro[inteiro["resultado"] != "IGNORADO_ATIVO"]
    assert set(decididos["decisao"]) <= set(partes["decisao"])
    pd.testing.assert_frame_equal(
        inteiro.set_index("decisao").loc[d[21:]], partes.set_index("decisao").loc[d[21:]]
    )


def test_igual_ao_simulador_da_fase_6b_com_entrada_deterministica() -> None:
    p = _precos(6 * 3600, semente=4)
    d = [int(x) for x in T0 + np.arange(0, 330, 3) * M]
    ex = Execucao(entrada_min_s=2, entrada_max_s=2)
    nosso = simular_eventos(_eventos(d), p, R5, _atr(d, 0.02), execucao=ex)
    sinais = _eventos(d).assign(atr=0.02)
    deles = simular(sinais, p, R5, entrada_aleatoria=True, entrada_max_ms=2000, tolerancia_atr=0.5)
    validos = nosso["resultado"] != "FORA_DA_JANELA"  # regra de janela é só do motor
    assert validos.sum() > 50
    juntos = nosso[validos].merge(deles, on="decisao", suffixes=("", "_6b"))
    # o 6b não conhece a janela: ele ocupa vencimentos que o motor recusa, então só as
    # operações que o 6b não ignorou são comparáveis
    comparaveis = juntos[juntos["resultado_6b"] != "IGNORADO_ATIVO"]
    comparaveis = comparaveis[comparaveis["resultado"] != "IGNORADO_ATIVO"]
    assert len(comparaveis) > 20
    assert (comparaveis["resultado"] == comparaveis["resultado_6b"]).all()
    assert (comparaveis["preco_entrada"] == comparaveis["preco_entrada_6b"]).all()


def test_sobreposicao_aplicada_depois_igual_a_simulacao_direta() -> None:
    from sinais.situacoes.simulacao import aplicar_sobreposicao

    p = _precos(6 * 3600, semente=9)
    d = [int(x) for x in T0 + np.arange(0, 330, 2) * M]
    atr = _atr(d, 0.05)
    direto = simular_eventos(_eventos(d), p, R15, atr)
    independente = simular_eventos(_eventos(d), p, R15, atr, sem_sobreposicao=False)
    assert (independente["resultado"] != "IGNORADO_ATIVO").all()
    depois = aplicar_sobreposicao(independente)
    pd.testing.assert_frame_equal(direto, depois)
    assert (depois["resultado"] == "IGNORADO_ATIVO").sum() > 10
    # subconjunto (ex.: só os sinais liberados pela camada B) = simular só esse subconjunto
    sub = d[::3]
    pd.testing.assert_frame_equal(
        aplicar_sobreposicao(independente[independente["decisao"].isin(sub)]),
        simular_eventos(_eventos(sub), p, R15, _atr(sub, 0.05)),
    )
