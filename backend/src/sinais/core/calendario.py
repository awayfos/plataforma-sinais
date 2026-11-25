"""Calendário de mercado por classe de ativo.

Fora do horário de negociação, o ativo fica "fechado": sem análise nem sinal.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo

from sinais.core.dominio import Ativo, ClasseAtivo
from sinais.core.tempo import InstanteMs, de_datetime, para_datetime, validar_instante

_NOVA_YORK = ZoneInfo("America/New_York")
_VIRADA_FX = time(17, 0)
_SEXTA, _SABADO, _DOMINGO = 4, 5, 6


class CalendarioMercado(Protocol):
    def aberto(self, instante: InstanteMs) -> bool: ...

    def proxima_abertura(self, instante: InstanteMs) -> InstanteMs | None: ...


class Calendario24x7:
    """Cripto: negociação contínua."""

    def aberto(self, instante: InstanteMs) -> bool:
        validar_instante(instante)
        return True

    def proxima_abertura(self, instante: InstanteMs) -> InstanteMs | None:
        return validar_instante(instante)


class CalendarioSemanalFx:
    """Forex e metais: de domingo 17:00 a sexta 17:00 em Nova York.

    O horário de verão dos EUA é tratado por ``zoneinfo``: em UTC a abertura
    acontece às 22:00 no inverno e às 21:00 no verão.
    """

    def aberto(self, instante: InstanteMs) -> bool:
        local = para_datetime(instante).astimezone(_NOVA_YORK)
        dia, hora = local.weekday(), local.time()
        if dia == _SABADO:
            return False
        if dia == _DOMINGO:
            return hora >= _VIRADA_FX
        if dia == _SEXTA:
            return hora < _VIRADA_FX
        return True

    def proxima_abertura(self, instante: InstanteMs) -> InstanteMs | None:
        if self.aberto(instante):
            return instante
        local = para_datetime(instante).astimezone(_NOVA_YORK)
        dias_ate_domingo = (_DOMINGO - local.weekday()) % 7
        data = local.date() + timedelta(days=dias_ate_domingo)
        return de_datetime(datetime.combine(data, _VIRADA_FX, tzinfo=_NOVA_YORK))


def calendario_para(ativo: Ativo) -> CalendarioMercado:
    if ativo.classe is ClasseAtivo.CRIPTO:
        return Calendario24x7()
    if ativo.classe in (ClasseAtivo.FOREX, ClasseAtivo.METAL):
        return CalendarioSemanalFx()
    raise NotImplementedError("calendário de ações: V1.1")
