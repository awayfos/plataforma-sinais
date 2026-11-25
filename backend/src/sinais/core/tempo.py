"""Tempo em UTC com milissegundos inteiros e relógio injetável.

Todo instante que cruza fronteiras de módulo é um ``InstanteMs``: inteiro de
milissegundos desde a época Unix, em UTC (ADR-13).
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from typing import Protocol

type InstanteMs = int

_UM_MS = timedelta(milliseconds=1)


def validar_instante(ms: object) -> InstanteMs:
    """Aceita só ``int`` (não ``bool``) maior ou igual a zero."""
    if isinstance(ms, bool) or not isinstance(ms, int):
        raise ValueError(f"instante deve ser int em milissegundos, recebido {type(ms).__name__}")
    if ms < 0:
        raise ValueError(f"instante deve ser >= 0, recebido {ms}")
    return ms


def de_datetime(dt: datetime) -> InstanteMs:
    """Converte um ``datetime`` com fuso para milissegundos UTC."""
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("datetime sem fuso horário não é aceito")
    delta = dt.astimezone(UTC) - datetime(1970, 1, 1, tzinfo=UTC)
    return validar_instante(delta // _UM_MS)


def para_datetime(ms: InstanteMs) -> datetime:
    """Converte milissegundos UTC para ``datetime`` em UTC."""
    validar_instante(ms)
    return datetime(1970, 1, 1, tzinfo=UTC) + ms * _UM_MS


def para_iso(ms: InstanteMs) -> str:
    """Formata como ISO 8601 em UTC com milissegundos, ex.: ``2026-11-25T03:00:00.123Z``."""
    dt = para_datetime(ms)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ms % 1000:03d}Z"


class Relogio(Protocol):
    def agora_ms(self) -> InstanteMs: ...


class RelogioSistema:
    """Relógio real do sistema (sincronizado por NTP no servidor)."""

    def agora_ms(self) -> InstanteMs:
        return time.time_ns() // 1_000_000


class RelogioFixo:
    """Relógio controlado manualmente, para testes."""

    def __init__(self, inicio_ms: InstanteMs) -> None:
        self._agora = validar_instante(inicio_ms)

    def agora_ms(self) -> InstanteMs:
        return self._agora

    def avancar(self, ms: int) -> None:
        self._agora = validar_instante(self._agora + ms)

    def definir(self, ms: InstanteMs) -> None:
        self._agora = validar_instante(ms)

