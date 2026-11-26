import numpy as np
import pandas as pd

from sinais.backtest.precos import SeriePrecos
from sinais.core.dominio import Expiracao
from sinais.corretoras.regras import EXNOVA
from sinais.situacoes.liquidacao import liquidar_sinal, registros_de
from sinais.situacoes.simulacao import simular_eventos

from ..analise.sinteticos import T0

M = 60_000


def _precos() -> SeriePrecos:
    t = T0 + np.arange(3 * 3600) * 1000
    c = 100 + np.cumsum(np.random.default_rng(2).normal(0, 0.01, len(t)))
    return SeriePrecos(t, c, c, 1000)


def test_registro_win_loss_empate_e_sem_dado() -> None:
    t = T0 + np.arange(1000) * 1000
    c = np.where(np.arange(1000) < 500, 100.0, 101.0)
    p = SeriePrecos(t, c, c, 1000)
    venc = T0 + 600_000
    r = liquidar_sinal("BTCUSDT", "S1", "S1", -1, 15, T0 + 5000, 100.0, venc, p)
    assert (r.resultado, r.preco_final, r.direcao) == ("LOSS", 101.0, "VENDA")
    assert r.titulo == "VENDA · BTCUSDT · 15 min"
    assert liquidar_sinal("BTCUSDT", "S1", "S1", 1, 15, T0, 100.0, venc, p).resultado == "WIN"
    assert liquidar_sinal("ETHUSDT", "S1", "S1", 1, 5, T0, 101.0, venc, p).resultado == "EMPATE"
    sem = liquidar_sinal("ETHUSDT", "S1", "S1", 1, 5, T0, 101.0, T0 + 3600_000, p)
    assert (sem.resultado, sem.preco_final) == ("SEM_DADO", None)


def test_registros_iguais_a_simulacao() -> None:
    p = _precos()
    d = [int(x) for x in T0 + np.arange(0, 150, 4) * M]
    ev = pd.DataFrame({"decisao": d, "direcao": [1, -1] * (len(d) // 2) + [1] * (len(d) % 2)})
    atr = pd.Series(1.0, index=pd.Index(d, dtype="int64"))
    ops = simular_eventos(ev, p, EXNOVA.regras[Expiracao.M15], atr)
    regs = registros_de(ops, "BTCUSDT", "S2", "S2", 15, p)
    liquidadas = ops[ops["resultado"].isin(["WIN", "LOSS", "TIE"])]
    assert len(regs) == len(liquidadas) > 3
    mapa = {"WIN": "WIN", "LOSS": "LOSS", "TIE": "EMPATE"}
    assert [r.resultado for r in regs] == [mapa[x] for x in liquidadas["resultado"]]
    assert [r.preco_entrada for r in regs] == liquidadas["preco_entrada"].tolist()
    assert [r.vencimento_t for r in regs] == liquidadas["vencimento_t"].tolist()
