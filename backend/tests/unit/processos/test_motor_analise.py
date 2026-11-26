import asyncio
import json
import math
import re
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from sinais.api.esquemas import Analise
from sinais.dados.modelos import Candle
from sinais.eventos.contratos import (
    STREAM_ANALISE_ATUALIZADA,
    evento_candle_fechado,
)
from sinais.eventos.memoria import PublicadorMemoria
from sinais.persistencia.analises import ArmazemAnalisesMemoria
from sinais.persistencia.memoria import RepositorioCandlesMemoria
from sinais.processos.motor_analise import MotorAnalise, montar_analise, montar_resumo

from ..analise.sinteticos import passeio

T0 = 1795575600000
M = 60_000


def linha(**valores: float) -> pd.DataFrame:
    """Snapshot de uma linha com os campos usados; o resto NaN."""
    base: dict[str, float] = {
        "ind_rsi": 72.346,
        "ind_macd_hist": -0.5,
        "ind_bb_pct": 0.91,
        "ind_atr_rel": 0.001,
        "ind_adx": 31.234,
        "ind_estoc_k": 88.8,
        "est_tendencia": 1.0,
        "est_bos": 0.0,
        "est_choch": 0.0,
        "est_dist_topo": 2.0,
        "est_dist_fundo": 3.0,
        "vol_relativo": 1.8,
        "vol_pressao": 0.45,
        "reg_res_dist": 0.4,
        "reg_sup_dist": 1.25,
        "reg_res_toques": 5.0,
        "reg_sup_toques": 1.0,
        "pa_impulso": 2.5,
        "pa_desaceleracao": -0.3,
        "pa_lateral": 0.0,
        "m5_est_tendencia": 1.0,
        "m15_est_tendencia": 1.0,
        "h1_est_tendencia": 1.0,
    }
    base.update(valores)
    return pd.DataFrame([base], index=pd.Index([T0], name="abertura"))


def test_montar_analise_mapeia_snapshot_para_contrato() -> None:
    a = montar_analise("BTCUSDT", linha(), "50000.10")
    assert a.simbolo == "BTCUSDT" and a.t == T0 and a.preco == "50000.10"
    assert a.tendencia == {"1m": 1, "5m": 1, "15m": 1, "1h": 1}
    assert a.forca_tendencia == 31.23
    atr = 50000.10 * 0.001
    assert a.indicadores.atr == pytest.approx(atr, abs=1e-4)
    assert a.indicadores.macd_hist == pytest.approx(-0.5 * atr, abs=1e-4)
    assert (a.indicadores.rsi, a.indicadores.bb_pct, a.indicadores.estoc_k) == (72.35, 0.91, 88.8)
    assert a.regioes.resistencia is not None
    assert a.regioes.resistencia.preco == pytest.approx(50000.10 + 0.4 * atr, abs=0.01)
    assert (a.regioes.resistencia.distancia_atr, a.regioes.resistencia.toques) == (0.4, 5)
    assert a.regioes.suporte is not None and a.regioes.suporte.toques == 1
    assert a.estrutura.topo == pytest.approx(50000.10 + 2 * atr, abs=0.01)
    assert a.estrutura.fundo == pytest.approx(50000.10 - 3 * atr, abs=0.01)
    assert a.estrutura.ultimo_evento is None
    assert (a.volume.relativo, a.volume.pressao_compradora) == (1.8, 0.45)
    assert (a.price_action.impulso, a.price_action.desaceleracao) == (2.5, -0.3)
    assert a.price_action.lateral is False


def test_ultimo_evento_procura_para_tras_e_choch_vence() -> None:
    s = pd.concat([linha(est_bos=1.0), linha(est_choch=-1.0, est_bos=-1.0), linha(), linha()])
    s.index = pd.Index([T0, T0 + M, T0 + 2 * M, T0 + 3 * M], name="abertura")
    a = montar_analise("BTCUSDT", s, "1")
    assert a.t == T0 + 3 * M
    assert a.estrutura.ultimo_evento == "CHOCH_BAIXA"
    assert montar_analise("BTCUSDT", s.iloc[:1], "1").estrutura.ultimo_evento == "BOS_ALTA"


def test_valores_ausentes_viram_null_e_tendencia_sem_contexto_zero() -> None:
    nan = math.nan
    s = linha(
        ind_rsi=nan,
        ind_atr_rel=nan,
        h1_est_tendencia=nan,
        reg_res_dist=nan,
        reg_sup_toques=0.0,
        pa_lateral=nan,
        est_dist_topo=nan,
    )
    a = montar_analise("ETHUSDT", s, "3000")
    assert a.indicadores.rsi is None and a.indicadores.atr is None
    assert a.indicadores.macd_hist is None
    assert a.tendencia["1h"] == 0
    assert a.regioes.resistencia is None and a.regioes.suporte is None
    assert a.estrutura.topo is None
    assert a.price_action.lateral is False
    texto = a.model_dump_json()
    assert "NaN" not in texto and "Infinity" not in texto


def _numeros(texto: str) -> list[float]:
    return [float(n.replace(",", ".")) for n in re.findall(r"-?\d+(?:,\d+)?", texto)]


def _valores(a: Analise) -> set[float]:
    vals: set[float] = set()

    def visitar(x: object) -> None:
        if isinstance(x, dict):
            for v in x.values():
                visitar(v)
        elif isinstance(x, list):
            for v in x:
                visitar(v)
        elif isinstance(x, (int, float)) and not isinstance(x, bool):
            vals.add(float(x))
            vals.add(abs(float(x)))

    d = a.model_dump()
    d.pop("resumo")
    visitar(d)
    return vals


@pytest.mark.parametrize(
    "valores",
    [
        {},
        {"est_tendencia": -1.0, "m5_est_tendencia": -1.0, "m15_est_tendencia": 0.0},
        {"ind_rsi": 25.0, "vol_relativo": 0.4, "vol_pressao": -0.5, "pa_lateral": 1.0},
        {"ind_adx": 12.0, "reg_res_toques": 1.0, "est_choch": 1.0},
        {
            f: 0.0
            for f in ("est_tendencia", "m5_est_tendencia", "m15_est_tendencia", "h1_est_tendencia")
        },
    ],
)
def test_resumo_nunca_inventa_numeros(valores: dict[str, float]) -> None:
    a = montar_analise("BTCUSDT", linha(**valores), "50000.10")
    assert a.resumo == montar_resumo(a)
    assert a.resumo
    conhecidos = _valores(a) | {1.0, 5.0, 15.0}  # rótulos de tempo gráfico (1m, 5m, 15m, 1h)
    for frase in a.resumo:
        for n in _numeros(frase):
            assert n in conhecidos, (frase, n)


def test_resumo_frases_do_contrato() -> None:
    a = montar_analise("BTCUSDT", linha(m5_est_tendencia=0.0), "50000.10")
    assert "Tendência de alta em 1m, 15m e 1h" in a.resumo
    assert "Preço a 0,4 ATR de uma resistência tocada 5 vezes" in a.resumo
    assert "Preço a 1,25 ATR de um suporte tocado 1 vez" in a.resumo
    assert "RSI em 72,35: região de sobrecompra" in a.resumo


# ----------------------------------------------------------------- motor ao vivo


def vela(i: int, df: pd.DataFrame) -> Candle:
    r = df.iloc[i]
    return Candle(
        "BTCUSDT",
        M,
        int(df.index[i]),
        Decimal(f"{r['o']:.2f}"),
        Decimal(f"{max(r['h'], r['o'], r['c']):.2f}") + Decimal("0.01"),
        Decimal(f"{min(r['l'], r['o'], r['c']):.2f}") - Decimal("0.01"),
        Decimal(f"{r['c']:.2f}"),
        Decimal(f"{r['v']:.4f}"),
        Decimal("1"),
        1,
        Decimal(f"{r['vb']:.4f}"),
        "binance",
    )


async def preparar(n: int = 400) -> tuple[RepositorioCandlesMemoria, list[Candle], pd.DataFrame]:
    df = passeio(n + 5)
    velas = [vela(i, df) for i in range(n + 5)]
    repo = RepositorioCandlesMemoria()
    await repo.inserir(velas[:n])
    return repo, velas, df


def test_motor_carrega_calcula_publica_e_guarda() -> None:
    async def caso() -> None:
        repo, velas, _ = await preparar()
        pub, armazem = PublicadorMemoria(), ArmazemAnalisesMemoria()
        motor = MotorAnalise(["BTCUSDT"], repo, armazem, pub, janela_min=300)
        await motor.carregar(velas[399].fechamento_ms)
        assert motor.ultima_abertura("BTCUSDT") == velas[399].abertura
        await repo.inserir([velas[400]])
        n = await motor.processar_lote([evento_candle_fechado(velas[400])])
        assert n == 1
        assert [s for s, _ in pub.publicados] == [STREAM_ANALISE_ATUALIZADA]
        campos = pub.publicados[0][1]
        assert campos["simbolo"] == "BTCUSDT" and campos["t"] == str(velas[400].abertura)
        guardada = await armazem.obter("BTCUSDT")
        assert guardada is not None and json.loads(guardada)["t"] == velas[400].abertura
        assert json.loads(campos["analise"]) == json.loads(guardada)
        assert Decimal(json.loads(guardada)["preco"]) == velas[400].fechamento
        assert len(motor.janela("BTCUSDT")) == 300

    asyncio.run(caso())


def test_motor_ignora_repetidos_outros_intervalos_e_simbolos() -> None:
    async def caso() -> None:
        repo, velas, _ = await preparar()
        pub, armazem = PublicadorMemoria(), ArmazemAnalisesMemoria()
        motor = MotorAnalise(["BTCUSDT"], repo, armazem, pub, janela_min=300)
        await motor.carregar(velas[399].fechamento_ms)
        ev_1s = dict(evento_candle_fechado(velas[399]), intervalo_ms="1000")
        ev_eth = dict(evento_candle_fechado(velas[399]), simbolo="ETHUSDT")
        assert await motor.processar_lote([evento_candle_fechado(velas[399]), ev_1s, ev_eth]) == 0
        assert pub.publicados == []

    asyncio.run(caso())


def test_motor_preenche_lacuna_pelo_banco_e_calcula_uma_vez_por_lote() -> None:
    async def caso() -> None:
        repo, velas, df = await preparar()
        pub, armazem = PublicadorMemoria(), ArmazemAnalisesMemoria()
        motor = MotorAnalise(["BTCUSDT"], repo, armazem, pub, janela_min=300)
        await motor.carregar(velas[399].fechamento_ms)
        await repo.inserir(velas[400:405])
        # só chegaram os eventos dos candles 402 e 404 (os outros se perderam)
        n = await motor.processar_lote(
            [evento_candle_fechado(velas[402]), evento_candle_fechado(velas[404])]
        )
        assert n == 1
        assert motor.ultima_abertura("BTCUSDT") == velas[404].abertura
        janela = motor.janela("BTCUSDT")
        assert [c.abertura for c in janela[-5:]] == [v.abertura for v in velas[400:405]]
        # o resultado é idêntico ao cálculo do zero com os mesmos 300 minutos
        do_zero = MotorAnalise(
            ["BTCUSDT"], repo, ArmazemAnalisesMemoria(), PublicadorMemoria(), 300
        )
        await do_zero.carregar(velas[404].fechamento_ms)
        assert do_zero.calcular("BTCUSDT") == motor.calcular("BTCUSDT")
        del df

    asyncio.run(caso())


def test_motor_sem_dados_nao_publica() -> None:
    async def caso() -> None:
        pub = PublicadorMemoria()
        motor = MotorAnalise(
            ["BTCUSDT"], RepositorioCandlesMemoria(), ArmazemAnalisesMemoria(), pub, 300
        )
        await motor.carregar(T0)
        assert motor.calcular("BTCUSDT") is None
        assert np.isnan(np.nan)

    asyncio.run(caso())


def test_decimal_texto_sem_zeros_e_sem_expoente() -> None:
    from sinais.api.esquemas import decimal_texto

    assert decimal_texto(Decimal("50000.100000000000")) == "50000.1"
    assert decimal_texto(Decimal("30000.000000000000")) == "30000"
    assert decimal_texto(Decimal("0E-12")) == "0"
    assert decimal_texto(Decimal("0.000012340000")) == "0.00001234"


def test_evento_envenenado_e_descartado_sem_travar_o_lote() -> None:
    async def caso() -> None:
        repo, velas, _ = await preparar()
        pub, armazem = PublicadorMemoria(), ArmazemAnalisesMemoria()
        motor = MotorAnalise(["BTCUSDT"], repo, armazem, pub, janela_min=300)
        await motor.carregar(velas[399].fechamento_ms)
        await repo.inserir([velas[400]])
        ruim = dict(evento_candle_fechado(velas[400]), abertura="nao-e-numero")
        r = await motor.processar_entradas(
            [("1-0", ruim), ("2-0", evento_candle_fechado(velas[400]))]
        )
        assert (r.publicadas, r.descartadas, r.falhas) == (1, ["1-0"], [])

    asyncio.run(caso())


def test_falha_de_calculo_deixa_so_os_eventos_do_simbolo_para_nova_tentativa() -> None:
    async def caso() -> None:
        repo, velas, _ = await preparar()
        pub, armazem = PublicadorMemoria(), ArmazemAnalisesMemoria()
        motor = MotorAnalise(["BTCUSDT", "ETHUSDT"], repo, armazem, pub, janela_min=300)
        await motor.carregar(velas[399].fechamento_ms)
        await repo.inserir([velas[400]])
        original = repo.listar

        async def listar(simbolo, *args):  # type: ignore[no-untyped-def]
            if simbolo == "ETHUSDT":
                raise RuntimeError("banco fora")
            return await original(simbolo, *args)

        repo.listar = listar  # type: ignore[method-assign]
        eth = dict(evento_candle_fechado(velas[400]), simbolo="ETHUSDT")
        r = await motor.processar_entradas(
            [("1-0", evento_candle_fechado(velas[400])), ("2-0", eth)]
        )
        assert (r.publicadas, r.descartadas, r.falhas) == (1, [], ["2-0"])

    asyncio.run(caso())


def test_pendentes_entregues_demais_vao_para_a_fila_morta() -> None:
    from sinais.processos.motor_analise import decidir_pendentes

    reprocessar, desistir = decidir_pendentes([("1-0", 1), ("2-0", 5), ("3-0", 4)], maximo=5)
    assert reprocessar == ["1-0", "3-0"] and desistir == ["2-0"]


def test_nome_do_consumidor_vem_do_ambiente_ou_do_host() -> None:
    import socket

    from sinais.processos.motor_analise import nome_consumidor

    assert nome_consumidor({"SINAIS_CONSUMIDOR": "motor-a"}) == "motor-a"
    assert nome_consumidor({}) == f"motor-{socket.gethostname()}"


def test_resumo_separa_sem_tendencia_de_sem_dados() -> None:
    a = montar_analise(
        "BTCUSDT",
        linha(
            est_tendencia=0.0,
            m5_est_tendencia=0.0,
            m15_est_tendencia=1.0,
            h1_est_tendencia=math.nan,
        ),
        "50000.10",
    )
    assert "Tendência de alta em 15m" in a.resumo
    assert "Sem tendência definida em 1m e 5m" in a.resumo
    assert "Sem dados de tendência em 1h" in a.resumo
    tudo_nan = {
        c: math.nan
        for c in ("est_tendencia", "m5_est_tendencia", "m15_est_tendencia", "h1_est_tendencia")
    }
    b = montar_analise("BTCUSDT", linha(**tudo_nan), "50000.10")
    assert "Sem dados de tendência em 1m, 5m, 15m e 1h" in b.resumo
    assert not any(f.startswith("Sem tendência definida") for f in b.resumo)


def test_resumo_nunca_diz_distancia_negativa() -> None:
    a = montar_analise(
        "BTCUSDT", linha(reg_res_dist=-0.3, reg_sup_dist=-0.2, vol_pressao=-0.5), "50000.10"
    )
    texto = " | ".join(a.resumo)
    assert "-0," not in texto and "a -" not in texto
    assert "Agressão vendedora predominante (0,5)" in a.resumo
