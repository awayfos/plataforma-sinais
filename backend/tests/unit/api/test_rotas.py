"""Rotas REST do contrato v1 com dublês em memória (FastAPI só no CI)."""

import asyncio
import json

import pytest

pytest.importorskip("fastapi")

from sinais.processos.motor_analise import montar_analise  # noqa: E402

from ..contas.dubles import SO_BTC, D, admin, cliente  # noqa: E402
from ..contas.dubles import T0 as T0_CONTAS  # noqa: E402
from ..contrato_candles import velas  # noqa: E402
from ..processos.test_motor_analise import linha  # noqa: E402
from .apoio import App, csrf, entrar, entrar_admin, montar  # noqa: E402

SENHA = "senha-forte-123"


def preparar(recursos: object = None, fim: int = T0_CONTAS + 30 * D) -> App:
    app = montar()
    kwargs = {} if recursos is None else {"recursos": recursos}
    asyncio.run(cliente(app.amb, fim=fim, **kwargs))  # type: ignore[arg-type]
    asyncio.run(admin(app.amb))
    return app


def erro_de(r: object) -> dict[str, str]:
    corpo = r.json()  # type: ignore[attr-defined]
    assert set(corpo) == {"erro"} and set(corpo["erro"]) == {"codigo", "mensagem"}
    return corpo["erro"]  # type: ignore[no-any-return]


def test_login_define_cookies_seguros_e_devolve_usuario() -> None:
    app = preparar()
    c = app.cliente()
    r = entrar(c, "ana@exemplo.com", SENHA)
    assert r.status_code == 200
    assert r.json()["usuario"] == {
        "id": r.json()["usuario"]["id"],
        "email": "ana@exemplo.com",
        "nome": "Ana",
        "papel": "cliente",
        "modo": "essencial",
        "assinatura": {
            "plano": "Plano BTCUSDT,ETHUSDT",
            "status": "ativa",
            "vence_em": T0_CONTAS + 30 * D,
        },
    }
    cookies = r.headers.get_list("set-cookie")
    sessao = next(x for x in cookies if x.startswith("sinais_sessao="))
    token_csrf = next(x for x in cookies if x.startswith("sinais_csrf="))
    for k in ("HttpOnly", "Secure", "SameSite=lax", "Path=/"):
        assert k.lower() in sessao.lower()
    assert "httponly" not in token_csrf.lower() and "secure" in token_csrf.lower()
    assert c.get("/api/eu").json()["email"] == "ana@exemplo.com"


def test_erros_de_login_no_formato_do_contrato() -> None:
    app = preparar()
    c = app.cliente()
    r = entrar(c, "ana@exemplo.com", "errada-errada")
    assert r.status_code == 401 and erro_de(r)["codigo"] == "credenciais_invalidas"
    r = entrar(c, "admin@exemplo.com", "senha-admin-123")
    assert r.status_code == 401 and erro_de(r)["codigo"] == "totp_necessario"
    r = c.post("/api/auth/login", json={"email": "x"})
    assert r.status_code == 422 and erro_de(r)["codigo"] == "validacao"


def test_rotas_sem_sessao_401_e_publico_aberto() -> None:
    c = preparar().cliente()
    for rota in ("/api/eu", "/api/ativos", "/api/candles?simbolo=BTCUSDT", "/api/admin/usuarios"):
        r = c.get(rota)
        assert r.status_code == 401 and erro_de(r)["codigo"] == "sessao_invalida", rota
    assert c.get("/api/publico/estatisticas").json() == []
    r = c.get("/api/nao-existe")
    assert r.status_code == 404 and erro_de(r)["codigo"] == "nao_encontrado"


def test_cabecalhos_de_seguranca() -> None:
    r = preparar().cliente().get("/api/publico/estatisticas")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert "default-src 'none'" in r.headers["content-security-policy"]
    assert r.headers["cache-control"] == "no-store"
    assert "max-age" in r.headers["strict-transport-security"]


def test_mutacao_exige_csrf() -> None:
    c = preparar().cliente()
    entrar(c, "ana@exemplo.com", SENHA)
    r = c.patch("/api/eu/preferencias", json={"layout": {"a": 1}})
    assert r.status_code == 403 and erro_de(r)["codigo"] == "csrf_invalido"
    r = c.patch("/api/eu/preferencias", json={"layout": {"a": 1}}, headers={"X-CSRF-Token": "x"})
    assert r.status_code == 403
    r = c.patch(
        "/api/eu/preferencias", json={"layout": {"a": 1}, "modo": "avancado"}, headers=csrf(c)
    )
    assert r.status_code == 200 and r.json()["modo"] == "avancado"


def test_trocar_senha_e_logout() -> None:
    app = preparar()
    c = app.cliente()
    entrar(c, "ana@exemplo.com", SENHA)
    r = c.post("/api/eu/senha", json={"senha_atual": SENHA, "senha_nova": "curta"}, headers=csrf(c))
    assert r.status_code == 422
    r = c.post(
        "/api/eu/senha",
        json={"senha_atual": SENHA, "senha_nova": "nova-senha-456"},
        headers=csrf(c),
    )
    assert r.status_code == 204
    r = c.post("/api/auth/logout", headers=csrf(c))
    assert r.status_code == 204
    assert c.get("/api/eu").status_code == 401
    assert c.post("/api/auth/logout").status_code == 204  # sem sessão: idempotente
    assert entrar(c, "ana@exemplo.com", "nova-senha-456").status_code == 200


def test_assinatura_vencida_402_nos_dados_mas_ve_a_conta() -> None:
    app = preparar(fim=T0_CONTAS + 3_600_000)
    c = app.cliente()
    entrar(c, "ana@exemplo.com", SENHA)
    assert c.get("/api/ativos").status_code == 200
    app.amb.relogio.avancar(3_600_000)
    for rota in ("/api/ativos", "/api/sinais?simbolo=BTCUSDT", "/api/analise?simbolo=BTCUSDT"):
        r = c.get(rota)
        assert r.status_code == 402 and erro_de(r)["codigo"] == "assinatura_vencida", rota
    assert c.get("/api/eu").json()["assinatura"]["status"] == "vencida"


def test_mercado_ativos_candles_analise_sinais() -> None:
    app = preparar(recursos=SO_BTC)
    c = app.cliente()
    entrar(c, "ana@exemplo.com", SENHA)
    assert [a["simbolo"] for a in c.get("/api/ativos").json()] == ["BTCUSDT"]
    asyncio.run(app.candles.inserir(velas(12)))
    ultimo = velas(12)[-1].abertura + 60_000
    r = c.get(f"/api/candles?simbolo=BTCUSDT&tg=1m&ate={ultimo}&limite=3")
    assert r.status_code == 200
    corpo = r.json()
    assert [x["t"] for x in corpo] == [v.abertura for v in velas(12)[-3:]]
    assert set(corpo[0]) == {"t", "o", "h", "l", "c", "v"} and isinstance(corpo[0]["o"], str)
    assert c.get(f"/api/candles?simbolo=BTCUSDT&tg=5m&ate={ultimo}").status_code == 200
    assert c.get("/api/candles?simbolo=BTCUSDT&tg=2m").status_code == 422
    assert c.get("/api/candles?simbolo=BTCUSDT&limite=1501").status_code == 422
    assert erro_de(c.get("/api/candles?simbolo=XRPUSDT"))["codigo"] == "ativo_desconhecido"
    r = c.get("/api/candles?simbolo=ETHUSDT")
    assert r.status_code == 403 and erro_de(r)["codigo"] == "ativo_nao_incluido"
    r = c.get("/api/analise?simbolo=BTCUSDT")
    assert r.status_code == 404 and erro_de(r)["codigo"] == "analise_indisponivel"
    analise = montar_analise("BTCUSDT", linha(), "50000.10")
    asyncio.run(app.analises.salvar("BTCUSDT", analise.model_dump_json()))
    assert c.get("/api/analise?simbolo=BTCUSDT").json() == json.loads(analise.model_dump_json())
    sinais = c.get("/api/sinais?simbolo=BTCUSDT").json()
    assert [s["expiracao"] for s in sinais] == ["1m", "5m"]  # o plano SO_BTC só tem 1m e 5m
    assert all(
        s["direcao"] == "AGUARDAR"
        and s["probabilidade"] is None
        and s["motivo"] == "Nenhum modelo validado para esta expiração"
        for s in sinais
    )
    assert c.get("/api/sinais/historico?simbolo=BTCUSDT").json() == []
    assert c.get("/api/sinais/historico?simbolo=BTCUSDT&inicio=10&fim=5").status_code == 422


def test_admin_fluxo_completo_e_cliente_sem_acesso() -> None:
    app = preparar()
    ana = app.cliente()
    entrar(ana, "ana@exemplo.com", SENHA)
    r = ana.get("/api/admin/usuarios")
    assert r.status_code == 403 and erro_de(r)["codigo"] == "sem_permissao"
    adm = app.cliente()
    entrar_admin(app, adm)
    h = csrf(adm)
    plano = {
        "nome": "Mensal BTC",
        "duracao_dias": 30,
        "preco_centavos": 9900,
        "recursos": {
            "ativos": ["BTCUSDT"],
            "expiracoes": ["1m", "5m"],
            "modo_avancado": False,
            "cursos": False,
        },
        "ativo": True,
    }
    assert adm.post("/api/admin/planos", json=plano).status_code == 403  # sem CSRF
    p = adm.post("/api/admin/planos", json=plano, headers=h)
    assert p.status_code == 201
    pid = p.json()["id"]
    assert (
        adm.patch(f"/api/admin/planos/{pid}", json={"preco_centavos": 12900}, headers=h).json()[
            "preco_centavos"
        ]
        == 12900
    )
    assert [x["nome"] for x in adm.get("/api/admin/planos").json()][-1] == "Mensal BTC"
    novo = {
        "email": "bia@exemplo.com",
        "nome": "Bia",
        "senha_temporaria": "temporaria-123",
        "plano": pid,
        "vence_em": None,
    }
    u = adm.post("/api/admin/usuarios", json=novo, headers=h)
    assert u.status_code == 201 and u.json()["status"] == "ativo"
    assert adm.post("/api/admin/usuarios", json=novo, headers=h).status_code == 409
    uid = u.json()["id"]
    a = adm.post(
        "/api/admin/assinaturas",
        json={"usuario_id": uid, "plano_id": pid, "inicio": T0_CONTAS, "fim": T0_CONTAS + 90 * D},
        headers=h,
    )
    assert a.status_code == 201 and a.json()["fim"] == T0_CONTAS + 90 * D
    lista = adm.get("/api/admin/usuarios?busca=bia").json()
    assert [x["email"] for x in lista] == ["bia@exemplo.com"]
    assert lista[0]["assinatura"]["vence_em"] == T0_CONTAS + 90 * D
    ana_id = ana.get("/api/eu").json()["id"]
    r = adm.patch(f"/api/admin/usuarios/{ana_id}", json={"status": "bloqueado"}, headers=h)
    assert r.status_code == 200 and r.json()["status"] == "bloqueado"
    assert ana.get("/api/eu").status_code == 401  # sessão derrubada na hora
    assert adm.get("/api/admin/usuarios?status=bloqueado").json()[0]["id"] == ana_id
    acessos = adm.get(f"/api/admin/acessos?usuario_id={ana_id}").json()
    assert acessos[0]["evento"] == "login" and set(acessos[0]) == {
        "id",
        "usuario_id",
        "evento",
        "ip",
        "user_agent",
        "t",
    }
    acoes = [x["acao"] for x in adm.get("/api/admin/auditoria").json()]
    assert acoes[:4] == ["usuario.editar", "assinatura.criar", "usuario.criar", "plano.editar"]
    payout = [{"simbolo": "BTCUSDT", "expiracao": "1m", "payout": 0.88}]
    assert adm.put("/api/admin/corretoras/exnova/payout", json=payout, headers=h).json() == payout
    assert adm.get("/api/admin/corretoras/exnova/payout").json() == payout
    ruim = [{"simbolo": "BTCUSDT", "expiracao": "1m", "payout": 1.5}]
    assert adm.put("/api/admin/corretoras/exnova/payout", json=ruim, headers=h).status_code == 422
    assert adm.get("/api/admin/qualidade").json() == []
    assert adm.patch("/api/admin/usuarios/9999", json={"nome": "x"}, headers=h).status_code == 404
