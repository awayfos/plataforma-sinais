import pandas as pd

from sinais.backtest.precos import SeriePrecos
from sinais.backtest.simulador import simular
from sinais.core.dominio import Expiracao
from sinais.corretoras.regras import EXNOVA

from ..analise.sinteticos import T0, M, quadro

UM = EXNOVA.regras[Expiracao.M1]
QUINZE = EXNOVA.regras[Expiracao.M15]


def sinais(*pares: tuple[int, int]) -> pd.DataFrame:
    return pd.DataFrame(pares, columns=["decisao", "direcao"])


def resultados(df: pd.DataFrame) -> list[str]:
    return [str(x) for x in df["resultado"]]


PRECOS = SeriePrecos.de_quadro(quadro([100.0, 101, 101, 99, 98, 97, 96]), M)


def test_compra_ganha_venda_perde() -> None:
    r = simular(sinais((T0 + M, 1)), PRECOS, UM)
    assert resultados(r) == ["WIN"]
    assert r["preco_entrada"][0] == 100.0 and r["preco_vencimento"][0] == 101.0
    assert r["vencimento_t"][0] == T0 + 2 * M
    assert resultados(simular(sinais((T0 + M, -1)), PRECOS, UM)) == ["LOSS"]


def test_empate() -> None:
    assert resultados(simular(sinais((T0 + 2 * M, 1)), PRECOS, UM)) == ["TIE"]


def test_fora_da_janela_com_latencia_alta() -> None:
    r = simular(sinais((T0 + M, 1)), PRECOS, UM, latencia_ms=31_000)
    assert resultados(r) == ["FORA_DA_JANELA"]


def test_ignora_sinal_com_outro_ativo() -> None:
    longo = SeriePrecos.de_quadro(quadro([100.0 + i for i in range(20)]), M)
    r = simular(sinais((T0 + M, 1), (T0 + 2 * M, 1)), longo, QUINZE)
    assert resultados(r)[0] == "WIN"
    assert resultados(r)[1] == "IGNORADO_ATIVO"


def test_sem_dado() -> None:
    r = simular(sinais((T0 + 20 * M, 1)), PRECOS, UM)
    assert resultados(r) == ["SEM_DADO"]


def test_margem_com_sinal_da_direcao() -> None:
    r = simular(sinais((T0 + 3 * M, -1)), PRECOS, UM)
    assert resultados(r) == ["WIN"]
    assert r["margem"][0] == 2.0


def test_decisao_fora_da_fronteira_com_precos_de_1m_vira_sem_dado() -> None:
    r = simular(sinais((T0 + M + 10_000, 1)), PRECOS, UM)
    assert resultados(r) == ["SEM_DADO"]


def test_entrada_aleatoria_dentro_da_janela_com_1s() -> None:
    idx = pd.Index([T0 + i * 1000 for i in range(200)], name="abertura")
    c = [100.0 + 0.01 * i for i in range(200)]
    df = pd.DataFrame({"o": c, "c": c}, index=idx)
    s1 = SeriePrecos.de_quadro(df, 1000)
    r = simular(sinais((T0 + M, 1), (T0 + 2 * M, 1)), s1, UM, entrada_aleatoria=True, semente=1)
    prazo = UM.prazo_compra(T0 + 2 * M)
    assert T0 + M + 2000 <= r["entrada_t"][0] <= prazo
    assert r["entrada_t"][0] % 1000 == 0
    assert resultados(r)[0] == "WIN"


def test_apertado_marcado() -> None:
    quase = SeriePrecos.de_quadro(quadro([100.0, 100.005, 100.005]), M)
    r = simular(sinais((T0 + M, 1)), quase, UM)
    assert bool(r["apertado"][0]) is True
