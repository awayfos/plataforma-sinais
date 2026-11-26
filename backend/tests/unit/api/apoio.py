"""Montagem do app com dublês em memória para os testes de rotas (precisa do FastAPI)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastapi.testclient import TestClient

from sinais.api.app import criar_app
from sinais.api.servicos import Servicos
from sinais.contas.admin import ServicoAdmin
from sinais.contas.limites import ContadorLimites
from sinais.contas.repositorio import RepositorioContas
from sinais.contas.servico import ParametrosContas
from sinais.persistencia.analises import ArmazemAnalises, ArmazemAnalisesMemoria
from sinais.persistencia.consultas_mercado import ConsultasMercado, ConsultasMercadoMemoria
from sinais.persistencia.memoria import RepositorioCandlesMemoria

from ..contas.dubles import T0, Ambiente, ambiente, codigo_totp

BASE = "https://testserver"


@dataclass
class App:
    amb: Ambiente
    servicos: Servicos
    candles: RepositorioCandlesMemoria
    analises: ArmazemAnalises
    campeoes: dict[tuple[str, str], str] = field(default_factory=dict)

    def cliente(self) -> TestClient:
        return TestClient(criar_app(self.servicos), base_url=BASE)


def montar(
    params: ParametrosContas | None = None,
    ws_verificacao_s: float = 0.05,
    repo: RepositorioContas | None = None,
    contador: ContadorLimites | None = None,
    mercado: ConsultasMercado | None = None,
    analises: ArmazemAnalises | None = None,
) -> App:
    amb = ambiente(params, repo, contador)
    candles = RepositorioCandlesMemoria()
    analises = analises if analises is not None else ArmazemAnalisesMemoria()
    campeoes: dict[tuple[str, str], str] = {}
    servicos = Servicos(
        contas=amb.servico,
        admin=ServicoAdmin(amb.servico, ("BTCUSDT", "ETHUSDT")),
        mercado=mercado if mercado is not None else ConsultasMercadoMemoria(candles),
        analises=analises,
        campeao=lambda s, e: campeoes.get((s, e)),
        ws_verificacao_s=ws_verificacao_s,
    )
    return App(amb, servicos, candles, analises, campeoes)


def entrar(c: TestClient, email: str, senha: str, totp: str | None = None) -> Any:
    corpo: dict[str, Any] = {"email": email, "senha": senha}
    if totp is not None:
        corpo["totp"] = totp
    return c.post("/api/auth/login", json=corpo)


def entrar_admin(app: App, c: TestClient) -> Any:
    r = entrar(c, "admin@exemplo.com", "senha-admin-123", codigo_totp(app.amb.relogio.agora_ms()))
    assert r.status_code == 200, r.text
    return r


def csrf(c: TestClient) -> dict[str, str]:
    return {"X-CSRF-Token": c.cookies.get("sinais_csrf") or ""}


__all__ = ["T0", "App", "csrf", "entrar", "entrar_admin", "montar"]
