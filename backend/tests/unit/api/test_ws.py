"""WebSocket ``/api/ws``: assinatura, fan-out, permissões e fechamento 4401/4402."""

import asyncio
from typing import Any

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402
from starlette.websockets import WebSocketDisconnect  # noqa: E402

from sinais.processos.motor_analise import montar_analise  # noqa: E402

from ..contas.dubles import SO_BTC, T0, D, admin, cliente, plano  # noqa: E402
from ..processos.test_motor_analise import linha  # noqa: E402
from .apoio import App, csrf, entrar, entrar_admin, montar  # noqa: E402

SENHA = "senha-forte-123"
H = 3_600_000


def preparar(recursos: Any = None, fim: int = T0 + 30 * D) -> App:
    app = montar()
    kwargs = {} if recursos is None else {"recursos": recursos}
    asyncio.run(cliente(app.amb, fim=fim, **kwargs))
    asyncio.run(admin(app.amb))
    return app


def cabecalho(c: TestClient) -> dict[str, str]:
    return {"cookie": f"sinais_sessao={c.cookies.get('sinais_sessao')}"}


def test_sem_sessao_fecha_4401() -> None:
    app = preparar()
    with app.cliente() as c, c.websocket_connect("/api/ws") as ws:
        with pytest.raises(WebSocketDisconnect) as e:
            ws.receive_json()
        assert e.value.code == 4401


def test_origem_de_outro_site_recusada() -> None:
    app = preparar()
    with app.cliente() as c:
        entrar(c, "ana@exemplo.com", SENHA)
        h = {**cabecalho(c), "origin": "https://malicioso.com"}
        with pytest.raises(WebSocketDisconnect) as e, c.websocket_connect("/api/ws", headers=h):
            pass
        assert e.value.code == 4403


def test_assinatura_vencida_na_conexao_fecha_4402() -> None:
    app = preparar(fim=T0 + 1)
    app.amb.relogio.avancar(1)
    with app.cliente() as c:
        entrar(c, "ana@exemplo.com", SENHA)
        with c.websocket_connect("/api/ws", headers=cabecalho(c)) as ws:
            with pytest.raises(WebSocketDisconnect) as e:
                ws.receive_json()
            assert e.value.code == 4402


def test_assinar_recebe_ultima_analise_e_atualizacoes() -> None:
    app = preparar()
    analise = montar_analise("BTCUSDT", linha(), "50000.10")
    asyncio.run(app.analises.salvar("BTCUSDT", analise.model_dump_json()))
    with app.cliente() as c:
        entrar(c, "ana@exemplo.com", SENHA)
        with c.websocket_connect("/api/ws", headers=cabecalho(c)) as ws:
            ws.send_json({"acao": "assinar", "canal": "analise:BTCUSDT"})
            msg = ws.receive_json()
            assert msg["canal"] == "analise:BTCUSDT" and msg["dados"]["preco"] == "50000.10"
            ws.send_json({"acao": "assinar", "canal": "candles:BTCUSDT:1m"})
            assert c.portal is not None
            candle = {
                "t": T0,
                "o": "1",
                "h": "2",
                "l": "0.5",
                "c": "1.5",
                "v": "3",
                "fechado": True,
            }
            c.portal.call(app.servicos.distribuidor.publicar, "candles:BTCUSDT:1m", candle)
            assert ws.receive_json() == {"canal": "candles:BTCUSDT:1m", "dados": candle}
            ws.send_json({"acao": "cancelar", "canal": "candles:BTCUSDT:1m"})
            ws.send_json({"acao": "assinar", "canal": "sinais:BTCUSDT"})
            sinais = ws.receive_json()
            assert sinais["canal"] == "sinais:BTCUSDT"
            assert [s["direcao"] for s in sinais["dados"]] == ["AGUARDAR"] * 5
            assert (
                c.portal.call(app.servicos.distribuidor.publicar, "candles:BTCUSDT:1m", candle) == 0
            )


def test_mensagem_invalida_e_ativo_fora_do_plano() -> None:
    app = preparar(recursos=SO_BTC)
    with app.cliente() as c:
        entrar(c, "ana@exemplo.com", SENHA)
        with c.websocket_connect("/api/ws", headers=cabecalho(c)) as ws:
            ws.send_text("lixo")
            assert ws.receive_json()["erro"]["codigo"] == "mensagem_invalida"
            ws.send_json({"acao": "assinar", "canal": "analise:ETHUSDT"})
            msg = ws.receive_json()
            assert (
                msg["canal"] == "analise:ETHUSDT" and msg["erro"]["codigo"] == "ativo_nao_incluido"
            )
            ws.send_json({"acao": "assinar", "canal": "sinais:BTCUSDT"})
            assert [s["expiracao"] for s in ws.receive_json()["dados"]] == ["1m", "5m"]
            assert c.portal is not None
            todas = [{"expiracao": e, "direcao": "AGUARDAR"} for e in ("1m", "5m", "15m")]
            c.portal.call(app.servicos.distribuidor.publicar, "sinais:BTCUSDT", todas)
            assert [s["expiracao"] for s in ws.receive_json()["dados"]] == ["1m", "5m"]


def test_vencimento_durante_a_conexao_fecha_4402() -> None:
    app = preparar(fim=T0 + H)
    with app.cliente() as c:
        entrar(c, "ana@exemplo.com", SENHA)
        with c.websocket_connect("/api/ws", headers=cabecalho(c)) as ws:
            ws.send_json({"acao": "assinar", "canal": "sinais:BTCUSDT"})
            ws.receive_json()
            app.amb.relogio.avancar(H)
            with pytest.raises(WebSocketDisconnect) as e:
                ws.receive_json()
            assert e.value.code == 4402
        r = c.get("/api/sinais?simbolo=BTCUSDT")
        assert r.status_code == 402


def test_bloqueio_pelo_admin_fecha_4401() -> None:
    app = preparar()
    with app.cliente() as c, app.cliente() as adm:
        entrar(c, "ana@exemplo.com", SENHA)
        ana_id = c.get("/api/eu").json()["id"]
        entrar_admin(app, adm)
        with c.websocket_connect("/api/ws", headers=cabecalho(c)) as ws:
            ws.send_json({"acao": "assinar", "canal": "sinais:BTCUSDT"})
            ws.receive_json()
            r = adm.patch(
                f"/api/admin/usuarios/{ana_id}", json={"status": "bloqueado"}, headers=csrf(adm)
            )
            assert r.status_code == 200
            with pytest.raises(WebSocketDisconnect) as e:
                ws.receive_json()
            assert e.value.code == 4401


def test_plano_reduzido_durante_a_conexao_cancela_o_canal_do_ativo() -> None:
    app = preparar()
    with app.cliente() as c:
        entrar(c, "ana@exemplo.com", SENHA)
        uid = c.get("/api/eu").json()["id"]
        with c.websocket_connect("/api/ws", headers=cabecalho(c)) as ws:
            ws.send_json({"acao": "assinar", "canal": "sinais:ETHUSDT"})
            assert ws.receive_json()["canal"] == "sinais:ETHUSDT"
            assert c.portal is not None

            async def rebaixar() -> None:
                p = await plano(app.amb, SO_BTC, nome="Só BTC")
                await app.amb.repo.criar_assinatura(uid, p.id, T0, T0 + 90 * D, "manual", T0)

            c.portal.call(rebaixar)
            msg = ws.receive_json()
            assert msg["canal"] == "sinais:ETHUSDT"
            assert msg["erro"]["codigo"] == "ativo_nao_incluido"
            assert c.portal.call(app.servicos.distribuidor.publicar, "sinais:ETHUSDT", []) == 0


def test_vela_em_formacao_no_websocket_com_foto_na_assinatura() -> None:
    from decimal import Decimal

    from sinais.api.velas import GestorVelas
    from sinais.core.tempo import RelogioFixo
    from sinais.dados.vela_formacao import Negocio
    from sinais.persistencia.memoria import RepositorioCandlesMemoria

    app = preparar()
    velas = GestorVelas(
        ["BTCUSDT", "ETHUSDT"],
        RepositorioCandlesMemoria(),
        RelogioFixo(T0),
        app.servicos.distribuidor,
    )
    app.servicos.velas = velas
    app.servicos.tarefas = [("velas", lambda: velas.executar(0.01))]
    velas.ao_negocio("BTCUSDT", Negocio(1, Decimal("100"), Decimal("1"), T0 + 5, False))
    velas.drenar()  # já "publicado": a próxima mensagem será só a foto da assinatura
    with app.cliente() as c:
        entrar(c, "ana@exemplo.com", SENHA)
        with c.websocket_connect("/api/ws", headers=cabecalho(c)) as ws:
            ws.send_json({"acao": "assinar", "canal": "candles:BTCUSDT:5m"})
            foto = ws.receive_json()
            assert foto == {
                "canal": "candles:BTCUSDT:5m",
                "dados": {
                    "t": T0,
                    "o": "100",
                    "h": "100",
                    "l": "100",
                    "c": "100",
                    "v": "1",
                    "fechado": False,
                },
            }
            ws.send_json({"acao": "assinar", "canal": "preco:BTCUSDT"})
            assert ws.receive_json()["dados"] == {"preco": "100", "t": T0 + 5}
            assert c.portal is not None
            n = Negocio(2, Decimal("101.5"), Decimal("2"), T0 + 9, False)
            c.portal.call(velas.ao_negocio, "BTCUSDT", n)
            recebidas: dict[str, dict[str, object]] = {}
            while len(recebidas) < 2:
                m = ws.receive_json()
                recebidas[m["canal"]] = m["dados"]
            assert recebidas["candles:BTCUSDT:5m"]["c"] == "101.5"
            assert recebidas["candles:BTCUSDT:5m"]["v"] == "3"
            assert recebidas["preco:BTCUSDT"] == {"preco": "101.5", "t": T0 + 9}
