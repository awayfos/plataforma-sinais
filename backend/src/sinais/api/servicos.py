"""Contêiner das dependências da API: a fábrica do app recebe tudo pronto (testes injetam
dublês em memória; o processo de produção liga PostgreSQL e Redis)."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

from sinais.api.sinais_ao_vivo import BuscaCampeao
from sinais.api.ws_canais import Distribuidor
from sinais.contas.admin import ServicoAdmin
from sinais.contas.servico import ServicoContas
from sinais.core.dominio import ATIVOS_V1, Ativo
from sinais.persistencia.analises import ArmazemAnalises
from sinais.persistencia.consultas_mercado import ConsultasMercado

NOMES_ATIVOS = {"BTCUSDT": "Bitcoin", "ETHUSDT": "Ethereum"}

type FonteEventos = Callable[["Servicos"], Coroutine[Any, Any, None]]


@dataclass
class Servicos:
    contas: ServicoContas
    admin: ServicoAdmin
    mercado: ConsultasMercado
    analises: ArmazemAnalises
    campeao: BuscaCampeao
    cookie_seguro: bool = True
    ws_verificacao_s: float = 5.0
    origens_permitidas: tuple[str, ...] = ()
    confiar_proxy: bool = False
    documentacao: bool = False
    ativos: tuple[Ativo, ...] = ATIVOS_V1
    distribuidor: Distribuidor = field(default_factory=Distribuidor)
    fonte_eventos: FonteEventos | None = None

    @property
    def simbolos(self) -> tuple[str, ...]:
        return tuple(a.simbolo for a in self.ativos)
