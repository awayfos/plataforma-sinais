"""WebSocket ``/api/ws``: assinatura, fan-out, permissões e fechamento 4401/4402."""

import asyncio
from typing import Any

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402
from starlette.websockets import WebSocketDisconnect  # noqa: E402

from sinais.processos.motor_analise import montar_analise  # noqa: E402

from ..contas.dubles import SO_BTC, T0, D, admin, cliente  # noqa: E402
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
