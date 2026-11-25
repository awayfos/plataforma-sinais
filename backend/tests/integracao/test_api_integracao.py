"""API com PostgreSQL/TimescaleDB e Redis reais: matriz de autorização, isolamento entre
usuários e perda imediata de acesso (REST e WebSocket) quando a assinatura vence."""

import json
import uuid
from collections.abc import Iterator
from typing import Any

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")
pytest.importorskip("redis")

from fastapi.testclient import TestClient  # noqa: E402
from redis.asyncio import Redis  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402
from starlette.websockets import WebSocketDisconnect  # noqa: E402

from sinais.api.eventos_redis import fonte_redis  # noqa: E402
from sinais.eventos.contratos import (  # noqa: E402
    STREAM_ANALISE_ATUALIZADA,
    evento_analise_atualizada,
)
from sinais.persistencia.analises import ArmazemAnalisesRedis  # noqa: E402
from sinais.persistencia.consultas_mercado import ConsultasMercadoPg  # noqa: E402
from sinais.persistencia.limites_redis import ContadorRedis  # noqa: E402
from sinais.persistencia.repositorio_contas_pg import RepositorioContasPg  # noqa: E402
from sinais.processos.motor_analise import montar_analise  # noqa: E402

from ..unit.api.apoio import App, montar  # noqa: E402
from ..unit.api.test_matriz_autorizacao import MATRIZ, PERFIS  # noqa: E402
from ..unit.contas.dubles import SO_BTC, T0, TODOS, D, admin, cliente, codigo_totp  # noqa: E402
from ..unit.processos.test_motor_analise import linha  # noqa: E402
from .banco import limpar_contas, migrar  # noqa: E402
from .conftest import exigir_db, exigir_redis  # noqa: E402

pytestmark = pytest.mark.integracao
SENHA = "senha-forte-123"
H = 3_600_000
EMAILS = {
    "vencido": "vencido@exemplo.com",
    "sem_assinatura": "sem@exemplo.com",
    "so_btc": "btc@exemplo.com",
    "completo": "completo@exemplo.com",
}


class Ambiente:
    """Um único TestClient (um único laço de eventos) com sessões trocadas por cabeçalho."""

    def __init__(self, app: App, c: TestClient, redis: Redis) -> None:
        self.app, self.c, self.redis = app, c, redis
        self.sessoes: dict[str, tuple[str, str]] = {}

    def chamar(self, fn: Any, *args: Any) -> Any:
        assert self.c.portal is not None
        return self.c.portal.call(fn, *args)

    def entrar(self, perfil: str, email: str, senha: str, totp: str | None = None) -> None:
        self.c.cookies.clear()
        corpo: dict[str, Any] = {"email": email, "senha": senha}
        if totp:
            corpo["totp"] = totp
        r = self.c.post("/api/auth/login", json=corpo)
        assert r.status_code == 200, r.text
        self.sessoes[perfil] = (r.cookies["sinais_sessao"], r.cookies["sinais_csrf"])
        self.c.cookies.clear()

    def cabecalhos(self, perfil: str, mutacao: bool = False) -> dict[str, str]:
        if perfil not in self.sessoes:
            return {}
        token, csrf = self.sessoes[perfil]
        h = {"cookie": f"sinais_sessao={token}; sinais_csrf={csrf}"}
        if mutacao:
            h["X-CSRF-Token"] = csrf
        return h

    def pedir(self, perfil: str, metodo: str, rota: str, corpo: Any = None) -> Any:
        self.c.cookies.clear()
        kwargs: dict[str, Any] = {"headers": self.cabecalhos(perfil, metodo != "GET")}
        if corpo is not None:
            kwargs["json"] = corpo
        return self.c.request(metodo, rota, **kwargs)


@pytest.fixture
def amb() -> Iterator[Ambiente]:
    url = migrar(exigir_db())
    engine = create_async_engine(url, poolclass=NullPool)
    redis = Redis.from_url(exigir_redis(), decode_responses=True)
    prefixo = f"teste:{uuid.uuid4().hex}:"
    app = montar(
        repo=RepositorioContasPg(engine),
        contador=ContadorRedis(redis, prefixo=prefixo),
        mercado=ConsultasMercadoPg(engine),
        analises=ArmazemAnalisesRedis(redis),
    )
    app.servicos.fonte_eventos = fonte_redis(redis, bloqueio_ms=100)
    with app.cliente() as c:
        a = Ambiente(app, c, redis)
        a.chamar(limpar_contas, engine)
        a.chamar(redis.delete, "analise:ultima:BTCUSDT", "analise:ultima:ETHUSDT")
        a.chamar(cliente, app.amb, EMAILS["vencido"], SENHA, SO_BTC, T0)
        a.chamar(cliente, app.amb, EMAILS["sem_assinatura"], SENHA, None)
        a.chamar(cliente, app.amb, EMAILS["so_btc"], SENHA, SO_BTC)
        a.chamar(cliente, app.amb, EMAILS["completo"], SENHA)
        a.chamar(admin, app.amb)
        for perfil, email in EMAILS.items():
            a.entrar(perfil, email, SENHA)
        a.entrar("admin", "admin@exemplo.com", "senha-admin-123", codigo_totp(T0))
        yield a
        a.chamar(redis.aclose)


def test_matriz_de_autorizacao_com_banco_real(amb: Ambiente) -> None:
    falhas = []
    for metodo, rota, corpo, esperado in MATRIZ:
        if metodo == "PATCH" and rota == "/api/eu/preferencias":
            esperado = (401, 403, 403, 403, 200, 200)  # o "vencido" aqui tem o plano SO_BTC
        obtido = tuple(amb.pedir(p, metodo, rota, corpo).status_code for p in PERFIS)
        if obtido != esperado:
            falhas.append((metodo, rota, dict(zip(PERFIS, obtido, strict=True))))
    assert falhas == []


def test_usuario_a_nunca_le_dados_de_b(amb: Ambiente) -> None:
    ra = amb.pedir("so_btc", "PATCH", "/api/eu/preferencias", {"layout": {"dono": "A"}})
    rb = amb.pedir("completo", "PATCH", "/api/eu/preferencias", {"layout": {"dono": "B"}})
    assert ra.status_code == rb.status_code == 200
    a, b = (
        amb.pedir("so_btc", "GET", "/api/eu").json(),
        amb.pedir("completo", "GET", "/api/eu").json(),
    )
    assert (a["email"], b["email"]) == (EMAILS["so_btc"], EMAILS["completo"])
    ua = amb.chamar(amb.app.amb.repo.usuario_por_id, a["id"])
    ub = amb.chamar(amb.app.amb.repo.usuario_por_id, b["id"])
    assert (ua.layout, ub.layout) == ({"dono": "A"}, {"dono": "B"})
    # token de B com o CSRF de A: recusado
    token_b, _ = amb.sessoes["completo"]
    _, csrf_a = amb.sessoes["so_btc"]
    amb.c.cookies.clear()
    r = amb.c.patch(
        "/api/eu/preferencias",
        json={"layout": {"dono": "A"}},
        headers={
            "cookie": f"sinais_sessao={token_b}; sinais_csrf={csrf_a}",
            "X-CSRF-Token": csrf_a,
        },
    )
    assert r.status_code == 403
    assert amb.chamar(amb.app.amb.repo.usuario_por_id, b["id"]).layout == {"dono": "B"}


def test_vencimento_tira_rest_e_ws_na_hora(amb: Ambiente) -> None:
    amb.chamar(cliente, amb.app.amb, "curto@exemplo.com", SENHA, TODOS, T0 + H)
    amb.entrar("curto", "curto@exemplo.com", SENHA)
    eu = amb.pedir("curto", "GET", "/api/eu").json()
    fim = eu["assinatura"]["vence_em"]
    assert fim == T0 + H
    h = amb.cabecalhos("curto")
    amb.c.cookies.clear()
    with amb.c.websocket_connect("/api/ws", headers=h) as ws:
        ws.send_json({"acao": "assinar", "canal": "sinais:BTCUSDT"})
        assert ws.receive_json()["canal"] == "sinais:BTCUSDT"
        amb.app.amb.relogio.definir(fim)
        with pytest.raises(WebSocketDisconnect) as e:
            ws.receive_json()
        assert e.value.code == 4402
    r = amb.pedir("curto", "GET", "/api/sinais?simbolo=BTCUSDT")
    assert r.status_code == 402 and r.json()["erro"]["codigo"] == "assinatura_vencida"
    # renovação pelo admin devolve o acesso na hora
    planos = amb.pedir("admin", "GET", "/api/admin/planos").json()
    pid = next(p["id"] for p in planos if "ETHUSDT" in p["recursos"]["ativos"])
    novo = {"usuario_id": eu["id"], "plano_id": pid, "inicio": fim, "fim": fim + 30 * D}
    assert amb.pedir("admin", "POST", "/api/admin/assinaturas", novo).status_code == 201
    assert amb.pedir("curto", "GET", "/api/sinais?simbolo=BTCUSDT").status_code == 200


def test_revogacao_fecha_ws_4401(amb: Ambiente) -> None:
    h = amb.cabecalhos("so_btc")
    uid = amb.pedir("so_btc", "GET", "/api/eu").json()["id"]
    amb.c.cookies.clear()
    with amb.c.websocket_connect("/api/ws", headers=h) as ws:
        ws.send_json({"acao": "assinar", "canal": "sinais:BTCUSDT"})
        ws.receive_json()
        r = amb.pedir("admin", "PATCH", f"/api/admin/usuarios/{uid}", {"status": "bloqueado"})
        assert r.status_code == 200
        with pytest.raises(WebSocketDisconnect) as e:
            ws.receive_json()
        assert e.value.code == 4401


def test_fan_out_do_redis_streams_ate_o_websocket(amb: Ambiente) -> None:
    # Sem verificação periódica no meio: o cliente fecha enquanto o servidor está ocioso.
    amb.app.servicos.ws_verificacao_s = 30
    analise = montar_analise("BTCUSDT", linha(), "50000.1")
    texto = analise.model_dump_json()
    h = amb.cabecalhos("so_btc")
    amb.c.cookies.clear()
    with amb.c.websocket_connect("/api/ws", headers=h) as ws:
        ws.send_json({"acao": "assinar", "canal": "analise:BTCUSDT"})
        ws.send_json({"acao": "assinar", "canal": "sinais:BTCUSDT"})
        assert ws.receive_json()["canal"] == "sinais:BTCUSDT"  # sem análise guardada ainda
        campos = evento_analise_atualizada("BTCUSDT", analise.t, texto)
        amb.chamar(amb.redis.xadd, STREAM_ANALISE_ATUALIZADA, campos)
        recebidas: dict[str, Any] = {}
        while len(recebidas) < 2:
            m = ws.receive_json()
            recebidas[m["canal"]] = m["dados"]
        assert recebidas["analise:BTCUSDT"] == json.loads(texto)
        assert [s["expiracao"] for s in recebidas["sinais:BTCUSDT"]] == ["1m", "5m"]
    amb.chamar(amb.app.analises.salvar, "BTCUSDT", texto)
    assert amb.pedir("so_btc", "GET", "/api/analise?simbolo=BTCUSDT").json() == json.loads(texto)
