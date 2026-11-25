"""Matriz papel × plano × rota (design §14). Cada célula é o status HTTP esperado."""

import asyncio
from collections.abc import Callable
from typing import Any

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from ..contas.dubles import SO_BTC, T0, D, admin, cliente  # noqa: E402
from .apoio import App, csrf, entrar, entrar_admin, montar  # noqa: E402

SENHA = "senha-forte-123"
PERFIS = ("anonimo", "vencido", "sem_assinatura", "so_btc", "completo", "admin")

# (método, rota, corpo) -> status por perfil, na ordem de PERFIS.
MATRIZ: list[tuple[str, str, Any, tuple[int, ...]]] = [
    ("GET", "/api/eu", None, (401, 200, 200, 200, 200, 200)),
    ("GET", "/api/ativos", None, (401, 402, 402, 200, 200, 200)),
    ("GET", "/api/candles?simbolo=BTCUSDT", None, (401, 402, 402, 200, 200, 200)),
    ("GET", "/api/candles?simbolo=ETHUSDT", None, (401, 402, 402, 403, 200, 200)),
    ("GET", "/api/analise?simbolo=ETHUSDT", None, (401, 402, 402, 403, 404, 404)),
    ("GET", "/api/sinais?simbolo=BTCUSDT", None, (401, 402, 402, 200, 200, 200)),
    ("GET", "/api/sinais?simbolo=ETHUSDT", None, (401, 402, 402, 403, 200, 200)),
    ("GET", "/api/sinais/historico?simbolo=BTCUSDT", None, (401, 402, 402, 200, 200, 200)),
    ("PATCH", "/api/eu/preferencias", {"modo": "avancado"}, (401, 200, 403, 403, 200, 200)),
    ("GET", "/api/publico/estatisticas", None, (200,) * 6),
    ("GET", "/api/admin/usuarios", None, (401, 403, 403, 403, 403, 200)),
    ("GET", "/api/admin/planos", None, (401, 403, 403, 403, 403, 200)),
    ("GET", "/api/admin/acessos", None, (401, 403, 403, 403, 403, 200)),
    ("GET", "/api/admin/auditoria", None, (401, 403, 403, 403, 403, 200)),
    ("GET", "/api/admin/qualidade", None, (401, 403, 403, 403, 403, 200)),
    ("GET", "/api/admin/corretoras/exnova/payout", None, (401, 403, 403, 403, 403, 200)),
    ("PUT", "/api/admin/corretoras/exnova/payout", [], (401, 403, 403, 403, 403, 200)),
    (
        "POST",
        "/api/admin/planos",
        {
            "nome": "P",
            "duracao_dias": 30,
            "preco_centavos": 1,
            "recursos": {"ativos": [], "expiracoes": [], "modo_avancado": False, "cursos": False},
        },
        (401, 403, 403, 403, 403, 201),
    ),
]


def montar_perfis() -> tuple[App, dict[str, TestClient]]:
    app = montar()

    async def criar() -> None:
        await cliente(app.amb, "vencido@exemplo.com", fim=T0)
        await cliente(app.amb, "sem@exemplo.com", recursos=None)
        await cliente(app.amb, "btc@exemplo.com", recursos=SO_BTC)
        await cliente(app.amb, "completo@exemplo.com", fim=T0 + 30 * D)
        await admin(app.amb)

    asyncio.run(criar())
    clientes = {p: app.cliente() for p in PERFIS}
    for perfil, email in (
        ("vencido", "vencido@exemplo.com"),
        ("sem_assinatura", "sem@exemplo.com"),
        ("so_btc", "btc@exemplo.com"),
        ("completo", "completo@exemplo.com"),
    ):
        assert entrar(clientes[perfil], email, SENHA).status_code == 200
    entrar_admin(app, clientes["admin"])
    return app, clientes


@pytest.fixture(scope="module")
def perfis() -> dict[str, TestClient]:
    return montar_perfis()[1]


def _chamar(c: TestClient, metodo: str, rota: str, corpo: Any) -> int:
    enviar: Callable[..., Any] = getattr(c, metodo.lower())
    kwargs: dict[str, Any] = {"headers": csrf(c)} if metodo != "GET" else {}
    if corpo is not None:
        kwargs["json"] = corpo
    return int(enviar(rota, **kwargs).status_code)


@pytest.mark.parametrize(
    ("metodo", "rota", "corpo", "esperado"), MATRIZ, ids=[f"{m} {r}" for m, r, _, _ in MATRIZ]
)
def test_matriz(
    perfis: dict[str, TestClient], metodo: str, rota: str, corpo: Any, esperado: tuple[int, ...]
) -> None:
    obtido = tuple(_chamar(perfis[p], metodo, rota, corpo) for p in PERFIS)
    assert dict(zip(PERFIS, obtido, strict=True)) == dict(zip(PERFIS, esperado, strict=True))


def test_usuario_a_nunca_le_dados_de_b() -> None:
    app, c = montar_perfis()
    a, b = c["so_btc"], c["completo"]
    h = csrf(a)
    assert (
        a.patch("/api/eu/preferencias", json={"layout": {"de": "A"}}, headers=h).status_code == 200
    )
    hb = csrf(b)
    assert (
        b.patch("/api/eu/preferencias", json={"layout": {"de": "B"}}, headers=hb).status_code == 200
    )
    ea, eb = a.get("/api/eu").json(), b.get("/api/eu").json()
    assert ea["email"] == "btc@exemplo.com" and eb["email"] == "completo@exemplo.com"
    assert ea["id"] != eb["id"]
    # o CSRF de B não serve na sessão de A
    r = a.patch("/api/eu/preferencias", json={"layout": {"x": 1}}, headers=hb)
    assert r.status_code == 403
    # a sessão de B não vale com o cookie CSRF de A
    tok_b = b.cookies.get("sinais_sessao")
    mista = app.cliente()
    mista.cookies.set("sinais_sessao", tok_b or "", domain="testserver")
    mista.cookies.set("sinais_csrf", a.cookies.get("sinais_csrf") or "", domain="testserver")
    assert mista.patch("/api/eu/preferencias", json={}, headers=csrf(mista)).status_code == 403
    # nenhuma rota de cliente aceita um id de outro usuário: não há parâmetro de usuário
    assert a.get(f"/api/eu?usuario_id={eb['id']}").json()["id"] == ea["id"]
    assert a.get(f"/api/admin/acessos?usuario_id={eb['id']}").status_code == 403
