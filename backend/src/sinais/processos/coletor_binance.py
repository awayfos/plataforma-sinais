"""Processo coletor: histórico por REST, tempo real por WebSocket, gravação e eventos.

Execução: ``python -m sinais.processos.coletor_binance``.
"""

from __future__ import annotations

import asyncio
import random
import signal
from collections.abc import Awaitable, Callable, Sequence

from sinais.core.dominio import ATIVOS_V1, TempoGrafico
from sinais.core.tempo import Relogio, RelogioSistema
from sinais.dados.agregacao import AgregadorIncremental
from sinais.dados.backfill import FonteHistorico, preencher
from sinais.dados.modelos import Candle, IntervaloColeta
from sinais.dados.provedores.backoff import atraso_backoff
from sinais.dados.provedores.binance.parsing import ErroParsing, de_mensagem_ws
from sinais.dados.provedores.erros import ErroLimiteTaxa
from sinais.eventos.contratos import STREAM_CANDLE_FECHADO, Publicador, evento_candle_fechado
from sinais.logs import obter_logger
from sinais.persistencia.repositorio import RepositorioCandles

_log = obter_logger(__name__)
_DIA_MS = 86_400_000
# Só baixa por REST candles que fecharam há pelo menos 2 s: protege contra relógio local
# adiantado e contra a Binance ainda não ter finalizado o candle.
MARGEM_MS = 2000
TEMPOS_DERIVADOS = tuple(t for t in TempoGrafico if t is not TempoGrafico.M1)


class Coletor:
    def __init__(
        self,
        simbolos: Sequence[str],
        intervalos: Sequence[IntervaloColeta],
        fonte: FonteHistorico,
        repo: RepositorioCandles,
        publicador: Publicador,
        relogio: Relogio,
        historico_dias: int,
        historico_dias_1s: int,
    ) -> None:
        self._simbolos = list(simbolos)
        self._intervalos = list(intervalos)
        self._fonte = fonte
        self._repo = repo
        self._pub = publicador
        self._relogio = relogio
        self._historico_ms = {
            IntervaloColeta.M1: historico_dias * _DIA_MS,
            IntervaloColeta.S1: historico_dias_1s * _DIA_MS,
        }
        self._agregadores = {
            s: [AgregadorIncremental(t) for t in TEMPOS_DERIVADOS] for s in self._simbolos
        }
        self._ultimo: dict[tuple[str, int], int] = {}
        self._pendentes: list[Candle] = []

    async def sincronizar(self, publicar: bool = False) -> None:
        """Preenche do último candle gravado (ou do início do histórico) até o candle atual."""
        referencia = self._relogio.agora_ms() - MARGEM_MS
        for simbolo in self._simbolos:
            for intervalo in self._intervalos:
                dur = intervalo.duracao_ms
                fim = referencia - referencia % dur
                ultima = await self._repo.ultima_abertura(simbolo, intervalo)
                inicio = ultima + dur if ultima is not None else fim - self._historico_ms[intervalo]
                if inicio < fim:
                    await preencher(
                        self._fonte,
                        self._repo,
                        simbolo,
                        intervalo,
                        inicio,
                        fim,
                        ao_gravar=self._publicar_lote if publicar else None,
                    )
                nova = await self._repo.ultima_abertura(simbolo, intervalo)
                if nova is not None:
                    self._ultimo[(simbolo, dur)] = nova

    async def ao_reconectar(self) -> None:
        """Republica o que falhou ao publicar e preenche o que fechou sem conexão."""
        pendentes, self._pendentes = self._pendentes, []
        await self._publicar_lote(pendentes)
        await self.sincronizar(publicar=True)

    async def ao_mensagem(self, texto: str) -> None:
        try:
            evento = de_mensagem_ws(texto)
        except ErroParsing as erro:
            _log.error("coletor.mensagem_invalida", extra={"campos": {"erro": str(erro)}})
            return
        if evento is None or not evento.fechado:
            return
        c = evento.candle
        intervalo = IntervaloColeta.S1 if c.intervalo_ms == 1000 else IntervaloColeta.M1
        chave = (c.simbolo, c.intervalo_ms)
        ultimo = self._ultimo.get(chave)
        if ultimo is None:
            ultimo = await self._repo.ultima_abertura(c.simbolo, intervalo)
        if ultimo is not None and c.abertura > ultimo + c.intervalo_ms:
            _log.warning(
                "coletor.lacuna_ao_vivo",
                extra={
                    "campos": {
                        "simbolo": c.simbolo,
                        "inicio": ultimo + c.intervalo_ms,
                        "fim": c.abertura,
                    }
                },
            )
            await preencher(
                self._fonte,
                self._repo,
                c.simbolo,
                intervalo,
                ultimo + c.intervalo_ms,
                c.abertura,
                ao_gravar=self._publicar_lote,
            )
        novo = await self._repo.inserir([c])
        self._ultimo[chave] = max(c.abertura, self._ultimo.get(chave, ultimo or 0))
        if novo:
            await self._publicar(c)

    async def _publicar_lote(self, candles: list[Candle]) -> None:
        for i, c in enumerate(candles):
            try:
                await self._publicar(c)
            except Exception:
                self._pendentes.extend(candles[i + 1 :])
                raise

    async def _publicar(self, c: Candle) -> None:
        """Publica ``c``. Se falhar, guarda para republicar na próxima reconexão."""
        try:
            await self._pub.publicar(STREAM_CANDLE_FECHADO, evento_candle_fechado(c))
        except Exception:
            self._pendentes.append(c)
            _log.error("coletor.publicacao_falhou", extra={"campos": {"simbolo": c.simbolo}})
            raise
        if c.intervalo_ms == IntervaloColeta.M1.duracao_ms and c.simbolo in self._agregadores:
            for ag in self._agregadores[c.simbolo]:
                maior = ag.adicionar(c)
                if maior is not None:
                    await self._pub.publicar(STREAM_CANDLE_FECHADO, evento_candle_fechado(maior))


async def com_novas_tentativas(
    tarefa: Callable[[], Awaitable[None]],
    dormir: Callable[[float], Awaitable[None]] = asyncio.sleep,
    aleatorio: Callable[[], float] = random.random,
) -> None:
    """Repete ``tarefa`` até concluir: bloqueio 418 espera o tempo pedido; outros erros, backoff."""
    tentativa = 0
    while True:
        try:
            await tarefa()
            return
        except asyncio.CancelledError:
            raise
        except ErroLimiteTaxa as erro:
            _log.error("coletor.bloqueio", extra={"campos": {"espera_s": erro.espera_s}})
            await dormir(erro.espera_s)
        except Exception as erro:
            espera = atraso_backoff(tentativa, aleatorio=aleatorio)
            tentativa += 1
            _log.error(
                "coletor.sincronizacao_falhou",
                extra={"campos": {"erro": repr(erro), "espera_s": espera}},
            )
            await dormir(espera)


async def principal() -> None:  # pragma: no cover - ligação de I/O
    import httpx
    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import create_async_engine

    from sinais.core.config import carregar_configuracao
    from sinais.dados.provedores.binance.rest import ClienteRestBinance
    from sinais.dados.provedores.binance.streams import (
        ConsumidorStreams,
        conector_websockets,
        nomes_streams,
        url_combinada,
    )
    from sinais.eventos.redis_streams import PublicadorRedis
    from sinais.logs import configurar_logs
    from sinais.persistencia.repositorio_pg import RepositorioCandlesPg
    from sinais.persistencia.url import url_async

    cfg = carregar_configuracao()
    configurar_logs(cfg.nivel_log)
    simbolos = [a.simbolo_provedor for a in ATIVOS_V1]
    intervalos = [IntervaloColeta.S1, IntervaloColeta.M1]
    engine = create_async_engine(url_async(cfg.database_url.get_secret_value()))
    redis = Redis.from_url(cfg.redis_url.get_secret_value(), decode_responses=True)
    parar = asyncio.Event()
    laco = asyncio.get_running_loop()
    for sinal in (signal.SIGTERM, signal.SIGINT):
        laco.add_signal_handler(sinal, parar.set)
    async with httpx.AsyncClient() as http:
        relogio = RelogioSistema()
        coletor = Coletor(
            simbolos,
            intervalos,
            ClienteRestBinance(cfg.binance_rest_url, http),
            RepositorioCandlesPg(engine),
            PublicadorRedis(redis),
            relogio,
            cfg.historico_dias,
            cfg.historico_dias_1s,
        )
        _log.info("coletor.iniciando", extra={"campos": {"simbolos": simbolos}})
        await com_novas_tentativas(coletor.sincronizar)
        url = url_combinada(cfg.binance_ws_url, nomes_streams(simbolos, intervalos))
        await ConsumidorStreams(
            url, conector_websockets, relogio, coletor.ao_mensagem, coletor.ao_reconectar
        ).executar(parar)
    await redis.aclose()
    await engine.dispose()
    _log.info("coletor.encerrado")


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(principal())
