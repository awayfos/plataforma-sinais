"""Vela em formação, negócio a negócio, para todos os tempos gráficos (1m a 1w).

Cada tempo gráfico mostra o período atual = minutos de 1m já fechados e **oficiais** (do banco
ou do evento ``candle.fechado``) + os negócios (aggTrade) dos minutos ainda não fechados.
Cada negócio vai para o minuto do seu horário ``T`` (abertura <= T < abertura + 60 s). Quando
chega o 1m oficial, ele substitui o parcial daquele minuto (reconciliação) e negócios com
``T`` anterior ao fim dele passam a ser descartados. Negócios repetidos (reconexão,
ressincronização por REST) são descartados pelo id do aggTrade, que cresce com o tempo: o
primeiro e o último do minuto são escolhidos pelo id, então a ordem de chegada não importa.

Regras iguais às da Binance: abertura = primeiro negócio, fechamento = último, máxima e mínima
dos preços, volume = soma das quantidades; semana começa segunda 00:00 UTC.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from sinais.core.dominio import TempoGrafico, abertura_candle
from sinais.core.tempo import InstanteMs
from sinais.dados.modelos import Candle

_M = 60_000
MAX_MINUTOS_ABERTOS = 180  # coleta de klines parada: não cresce sem limite


@dataclass(frozen=True, slots=True)
class Negocio:
    id: int
    preco: Decimal
    qtd: Decimal
    t: InstanteMs
    comprador_maker: bool


@dataclass(frozen=True, slots=True)
class Vela:
    tg: TempoGrafico
    t: InstanteMs
    o: Decimal
    h: Decimal
    l: Decimal  # noqa: E741 - nome do OHLC
    c: Decimal
    v: Decimal


@dataclass(slots=True)
class _Trecho:
    """OHLCV de um pedaço do período (minuto parcial ou soma de minutos oficiais)."""

    o: Decimal
    h: Decimal
    l: Decimal  # noqa: E741
    c: Decimal
    v: Decimal


@dataclass(slots=True)
class _Minuto:
    abertura: InstanteMs
    trecho: _Trecho
    id_o: int
    id_c: int
    t_c: InstanteMs
    ids: set[int] = field(default_factory=set)


@dataclass(slots=True)
class _Oficial:
    periodo: InstanteMs
    trecho: _Trecho


def _juntar(trechos: Iterable[_Trecho]) -> _Trecho | None:
    total: _Trecho | None = None
    for t in trechos:
        if total is None:
            total = _Trecho(t.o, t.h, t.l, t.c, t.v)
        else:
            total.h = max(total.h, t.h)
            total.l = min(total.l, t.l)
            total.c = t.c
            total.v += t.v
    return total


class VelaEmFormacao:
    def __init__(self, simbolo: str, tempos: Sequence[TempoGrafico] = tuple(TempoGrafico)) -> None:
        self.simbolo = simbolo
        self.tempos = tuple(tempos)
        self._fechado_ate: InstanteMs | None = None
        self._minutos: dict[InstanteMs, _Minuto] = {}
        self._oficiais: dict[TempoGrafico, _Oficial] = {}
        self.precisa_recarregar = False

    @property
    def fechado_ate(self) -> InstanteMs | None:
        """Fim do último 1m oficial aplicado (None: nenhum)."""
        return self._fechado_ate

    # ---------------------------------------------------------- oficiais (1m)
    def carregar(self, fechados_1m: Sequence[Candle]) -> None:
        """Recomeça a partir dos candles de 1m oficiais do período atual (ordem crescente),
        mantendo os negócios de minutos posteriores ao último deles."""
        self._oficiais.clear()
        self._fechado_ate = None
        for c in fechados_1m:
            self._somar_oficial(c)
            self._fechado_ate = c.fechamento_ms
        self._descartar_fechados()
        self.precisa_recarregar = False

    def fechar_1m(self, c: Candle) -> bool:
        """Reconcilia com o 1m oficial. Devolve se foi aplicado (repetido/antigo → False).

        Sem nenhum oficial carregado (banco vazio na carga) ou com lacuna antes deste, a soma
        oficial dos períodos (4h, 1d, 1w...) ficaria incompleta: pede recarga do banco."""
        if self._fechado_ate is not None and c.abertura < self._fechado_ate:
            return False
        if self._fechado_ate is None or c.abertura > self._fechado_ate:
            self.precisa_recarregar = True
        self._somar_oficial(c)
        self._fechado_ate = c.fechamento_ms
        self._descartar_fechados()
        return True

    def _somar_oficial(self, c: Candle) -> None:
        trecho = _Trecho(c.abertura_preco, c.maxima, c.minima, c.fechamento, c.volume)
        for tg in self.tempos:
            periodo = abertura_candle(c.abertura, tg)
            atual = self._oficiais.get(tg)
            if atual is None or atual.periodo < periodo:
                self._oficiais[tg] = _Oficial(periodo, _Trecho(**_campos(trecho)))
            elif atual.periodo == periodo:
                t = atual.trecho
                t.h, t.l, t.c, t.v = (
                    max(t.h, trecho.h),
                    min(t.l, trecho.l),
                    trecho.c,
                    t.v + trecho.v,
                )

    def _descartar_fechados(self) -> None:
        if self._fechado_ate is None:
            return
        for m in [m for m in self._minutos if m < self._fechado_ate]:
            del self._minutos[m]

    # --------------------------------------------------------------- negócios
    def adicionar(self, n: Negocio) -> bool:
        """Acrescenta um negócio. Devolve False se repetido ou de minuto já fechado."""
        if self._fechado_ate is not None and n.t < self._fechado_ate:
            return False
        abertura = n.t - n.t % _M
        m = self._minutos.get(abertura)
        if m is None:
            self._minutos[abertura] = _Minuto(
                abertura,
                _Trecho(n.preco, n.preco, n.preco, n.preco, n.qtd),
                n.id,
                n.id,
                n.t,
                {n.id},
            )
            while len(self._minutos) > MAX_MINUTOS_ABERTOS:
                del self._minutos[min(self._minutos)]
            return True
        if n.id in m.ids:
            return False
        m.ids.add(n.id)
        t = m.trecho
        t.h = max(t.h, n.preco)
        t.l = min(t.l, n.preco)
        t.v += n.qtd
        if n.id < m.id_o:
            m.id_o, t.o = n.id, n.preco
        if n.id > m.id_c:
            m.id_c, t.c, m.t_c = n.id, n.preco, n.t
        return True

    # --------------------------------------------------------------- leitura
    def minuto(self, abertura: InstanteMs) -> Vela | None:
        """Minuto montado só com negócios (antes da reconciliação)."""
        m = self._minutos.get(abertura)
        if m is None:
            return None
        t = m.trecho
        return Vela(TempoGrafico.M1, abertura, t.o, t.h, t.l, t.c, t.v)

    def vela(self, tg: TempoGrafico) -> Vela | None:
        """Vela em formação de ``tg``: o período do negócio mais recente."""
        if not self._minutos:
            return None
        periodo = abertura_candle(max(self._minutos), tg)
        fim = periodo + tg.duracao_ms
        trechos: list[_Trecho] = []
        oficial = self._oficiais.get(tg)
        if oficial is not None and oficial.periodo == periodo and tg is not TempoGrafico.M1:
            trechos.append(oficial.trecho)
        trechos.extend(self._minutos[m].trecho for m in sorted(self._minutos) if periodo <= m < fim)
        total = _juntar(trechos)
        if total is None:  # pragma: no cover - o minuto mais recente está sempre no período
            return None
        return Vela(tg, periodo, total.o, total.h, total.l, total.c, total.v)

    def ultimo_preco(self) -> tuple[Decimal, InstanteMs] | None:
        if not self._minutos:
            return None
        m = self._minutos[max(self._minutos)]
        return m.trecho.c, m.t_c


def _campos(t: _Trecho) -> dict[str, Decimal]:
    return {"o": t.o, "h": t.h, "l": t.l, "c": t.c, "v": t.v}
