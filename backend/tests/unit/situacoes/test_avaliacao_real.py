"""Ponta a ponta da rodada de avaliação com dados sintéticos de 1 s (períodos curtos)."""

import numpy as np
import pandas as pd

from sinais.analise.indicadores import atr
from sinais.backtest.precos import SeriePrecos
from sinais.backtest.walk_forward import Dobra
from sinais.features.microestrutura import agregar_segundos, features_microestrutura
from sinais.situacoes.avaliacao_real import ProcessadoAtivo, avaliar, processar_ativo
from sinais.situacoes.parametros import VARIACOES
from sinais.situacoes.periodos import Periodos
from sinais.situacoes.relatorio import REGRAS
from sinais.situacoes.simulacao import simular_eventos

from ..analise.sinteticos import T0
from ..features.sinteticos_1s import para_1m, passeio_1s

H = 3_600_000


def _periodos() -> Periodos:
    ds = [
        Dobra((T0 + a * H, T0 + (a + 24) * H), (T0 + (a + 24) * H, T0 + (a + 32) * H),
              (T0 + (a + 32) * H, T0 + (a + 40) * H))
        for a in (0, 8, 16)
    ]  # fmt: skip
    return Periodos(T0, T0 + 72 * H, ds, (T0 + 56 * H, T0 + 72 * H), (T0 + 48 * H, T0 + 56 * H),
                    (T0 + 24 * H, T0 + 48 * H))  # fmt: skip


def test_rodada_ponta_a_ponta_sintetica() -> None:
    per = _periodos()
    procs = []
    entradas = {}
    for k, ativo in enumerate(("BTCUSDT", "ETHUSDT")):
        s1 = passeio_1s(72 * 60, semente=10 + k)
        s1[["o", "h", "l", "c"]] = s1[["o", "h", "l", "c"]] * 10  # amplitude maior: mais eventos
        m1 = para_1m(s1)
        precos = SeriePrecos(s1.index.to_numpy(), s1["c"].to_numpy(), s1["c"].to_numpy(), 1000)
        micro = features_microestrutura(agregar_segundos(s1))
        procs.append(processar_ativo(ativo, m1, precos, micro, per, REGRAS))
        entradas[ativo] = (m1, precos)
    assert sum(len(p.eventos) for p in procs) > 100
    r = avaliar(procs, per, REGRAS, 0.86)
    a = [x for x in r.linhas if x.camada == "A"]
    assert len(a) == 10 * 2 * 2 * 3
    assert all(r.b[k] is None for k in r.b)  # poucas linhas: camada B não tentada
    assert all(x.recomendacao != "candidata" for x in r.linhas)
    com_ops = [x for x in a if x.teste.wins + x.teste.losses > 0]
    assert com_ops
    # a mesma chave simulada direto (sem a etapa um a um) dá as mesmas métricas
    p = procs[0]
    x = next(x for x in com_ops if x.ativo == "BTCUSDT" and x.expiracao == "15m")
    m = (p.eventos["variacao"] == x.variacao) & (p.eventos["espelho"] == x.espelho)
    m &= (p.eventos["decisao"] >= per.teste[0]) & (p.eventos["decisao"] < per.teste[1])
    m1, precos = entradas["BTCUSDT"]
    atr_dec = pd.Series(atr(m1, 14).to_numpy(), index=m1.index.to_numpy() + 60_000)
    res = simular_eventos(p.eventos[m], precos, REGRAS["15m"], atr_dec)["resultado"]
    assert (int((res == "WIN").sum()), int((res == "LOSS").sum())) == (x.teste.wins, x.teste.losses)
    assert np.isfinite(x.melhor_baseline)


def _processado_artificial(ativo: str, semente: int) -> ProcessadoAtivo:
    """Eventos S2 espalhados nos 24 meses reais; a situação vence 75% quando ``ctx`` (aqui
    ``dist_sr_atr``) > 1 e 50% no resto. Sem preços: a simulação um a um já vem pronta."""
    from sinais.situacoes.periodos import periodos_descoberta

    per = periodos_descoberta("2026-10", 24)
    rng = np.random.default_rng(semente)
    n = 30_000
    d = np.unique(rng.integers(per.inicio, per.fim - H, n) // 60_000 * 60_000)
    n = len(d)
    ctx = rng.normal(0, 1, n)
    vence = rng.random(n) < np.where(ctx > 1, 0.75, 0.5)
    espelho = rng.choice(["topo", "fundo"], n)
    eventos = pd.DataFrame(
        {
            "decisao": d, "situacao": "S2", "variacao": "S2", "espelho": espelho,
            "direcao": np.where(espelho == "topo", -1, 1), "nivel": 1.0, "ordem_toque": 4.0,
            "min_entre_toques": 10.0, "dist_sr_atr": ctx, "queda_pressao": 0.0,
            "confluencias": 0, "conflito": False, "ativo": ativo,
        }
    )  # fmt: skip
    ops = pd.DataFrame(
        {
            "decisao": d, "direcao": eventos["direcao"], "entrada_t": d + 5000,
            "vencimento_t": d + 900_000, "tempo_restante_s": 895, "preco_decisao": 1.0,
            "preco_entrada": 1.0, "preco_vencimento": 1.0, "apertado": False,
            "resultado": np.where(vence, "WIN", "LOSS"),
        }
    )  # fmt: skip
    base = ops.iloc[::2][["decisao", "direcao", "vencimento_t", "resultado"]].copy()
    base["resultado"] = np.where(np.arange(len(base)) % 2 == 0, "WIN", "LOSS")
    snap = pd.DataFrame({"ind_x": rng.normal(0, 1, n)}, index=pd.Index(d - 60_000))
    contagem = pd.DataFrame(
        [{"ativo": ativo, "variacao": v.nome, "espelho": e, "expiracao": "15m", "elegivel": True}
         for v in VARIACOES for e in ("topo", "fundo")]
    )  # fmt: skip
    alea = base.assign(u=0.5)
    return ProcessadoAtivo(
        ativo, eventos, {"15m": ops}, {"15m": {"sempre_compra": base}}, {"15m": alea}, snap,
        contagem, 600_000, 0,
    )  # fmt: skip


def test_camada_b_ponta_a_ponta_com_sinal_plantado() -> None:
    from sinais.situacoes.periodos import periodos_descoberta

    per = periodos_descoberta("2026-10", 24)
    procs = [_processado_artificial("BTCUSDT", 1), _processado_artificial("ETHUSDT", 2)]
    r = avaliar(procs, per, {"15m": REGRAS["15m"]}, 0.86)
    assert r.b[("S2", "15m")] is not None
    assert r.b[("S1", "15m")] is None  # sem eventos: não tentada
    b = [x for x in r.linhas if x.camada == "B"]
    a = {(x.ativo, x.espelho): x for x in r.linhas if x.camada == "A" and x.variacao == "S2"}
    assert len(b) == 4
    for x in b:
        assert x.teste.taxa > a[(x.ativo, x.espelho)].teste.taxa + 0.05
        assert x.p_b_supera_a < 0.05
    assert any(x.recomendacao == "candidata" for x in b)


def test_markdown_do_resultado_tem_todas_as_linhas_e_a_conclusao() -> None:
    from sinais.situacoes.periodos import periodos_descoberta
    from sinais.situacoes.relatorio import candidatas_json, markdown_resultado

    per = periodos_descoberta("2026-10", 24)
    procs = [_processado_artificial("BTCUSDT", 1), _processado_artificial("ETHUSDT", 2)]
    r = avaliar(procs, per, {"15m": REGRAS["15m"]}, 0.86)
    texto = markdown_resultado(r, {"fonte": "sintética"})
    assert texto.count("| BTCUSDT | S2 | topo | 15m |") == 2  # camadas A e B
    assert "| BTCUSDT | S2 | topo | 4º |" in texto  # diagnóstico por ordem do toque
    assert "## Conclusão" in texto and "candidata" in texto
    assert "Camada B" in texto
    js = candidatas_json(r)
    assert all(c["camada"] == "B" and c["variacao"] == "S2" for c in js) and js
