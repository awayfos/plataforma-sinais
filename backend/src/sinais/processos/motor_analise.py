"""Motor de análise ao vivo (Fase 7): ``candle.fechado`` (1m) → snapshot fs-1 → ``Analise``.

Mantém os últimos ``JANELA_AO_VIVO_1M`` minutos por símbolo (carregados do banco no início),
recalcula o snapshot com o mesmo código do laboratório (``sinais.features.snapshot``) e publica
``analise.atualizada`` com a ``Analise`` do contrato. A última análise de cada símbolo fica
guardada para ``GET /api/analise``.

``montar_analise`` e ``montar_resumo`` são puros. O resumo é montado por templates só com os
números da própria ``Analise`` (ADR-10): nenhum número é inventado.

Execução: ``python -m sinais.processos.motor_analise``.
"""

from __future__ import annotations

import asyncio
import math
import os
import signal
import socket
from collections import deque
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import pandas as pd

from sinais.analise.quadro import para_quadro
from sinais.api.esquemas import (
    Analise,
    Estrutura,
    EventoEstrutura,
    Indicadores,
    PriceAction,
    Regiao,
    Regioes,
    TempoTendencia,
    VolumeAnalise,
    decimal_texto,
)
from sinais.dados.modelos import Candle, IntervaloColeta
from sinais.eventos.contratos import (
    STREAM_ANALISE_ATUALIZADA,
    STREAM_CANDLE_FECHADO,
    Publicador,
    evento_analise_atualizada,
)
from sinais.features.snapshot import JANELA_AO_VIVO_1M, montar_snapshot
from sinais.logs import obter_logger
from sinais.persistencia.analises import ArmazemAnalises
from sinais.persistencia.repositorio import RepositorioCandles

_log = obter_logger(__name__)
_M = 60_000
GRUPO = "motor_analise"
_TENDENCIAS: tuple[tuple[TempoTendencia, str], ...] = (
    ("1m", "est_tendencia"),
    ("5m", "m5_est_tendencia"),
    ("15m", "m15_est_tendencia"),
    ("1h", "h1_est_tendencia"),
)


def _num(x: object, casas: int = 2) -> float | None:
    if x is None:
        return None
    v = float(x)  # type: ignore[arg-type]
    if not math.isfinite(v):
        return None
    r = round(v, casas)
    return 0.0 if r == 0 else r


def _sinal(x: object) -> int:
    v = _num(x)
    if v is None or v == 0:
        return 0
    return 1 if v > 0 else -1


def _ultimo_evento(snapshot: pd.DataFrame) -> EventoEstrutura | None:
    if "est_bos" not in snapshot or "est_choch" not in snapshot:
        return None
    choch = snapshot["est_choch"].to_numpy()
    bos = snapshot["est_bos"].to_numpy()
    for i in range(len(snapshot) - 1, -1, -1):
        if choch[i] == choch[i] and choch[i] != 0:
            return "CHOCH_ALTA" if choch[i] > 0 else "CHOCH_BAIXA"
        if bos[i] == bos[i] and bos[i] != 0:
            return "BOS_ALTA" if bos[i] > 0 else "BOS_BAIXA"
    return None


def montar_analise(
    simbolo: str, snapshot: pd.DataFrame, preco: str, casas_preco: int = 2
) -> Analise:
    """``Analise`` do contrato a partir da última linha do snapshot fs-1.

    O ATR em preço é ``ind_atr_rel × preço``; distâncias em ATR viram preços com ele. Valores
    sem histórico suficiente (NaN) viram ``null``; tendência sem contexto vira 0.
    """
    linha = snapshot.iloc[-1]

    def campo(nome: str) -> float:
        valor = linha.get(nome, math.nan)
        return float(valor) if valor is not None else math.nan

    c = float(preco)
    atr = c * campo("ind_atr_rel")
    atr_ok = math.isfinite(atr) and atr > 0

    def preco_a(distancia_atr: float) -> float | None:
        if not atr_ok or not math.isfinite(distancia_atr):
            return None
        return _num(c + distancia_atr * atr, casas_preco)

    def regiao(dist: str, toques: str, sentido: int) -> Regiao | None:
        d, n = campo(dist), campo(toques)
        p = preco_a(sentido * d)
        if p is None or not math.isfinite(n) or n < 1:
            return None
        return Regiao(preco=p, distancia_atr=_num(d) or 0.0, toques=int(n))

    analise = Analise(
        simbolo=simbolo,
        t=int(snapshot.index[-1]),
        preco=preco,
        tendencia={rotulo: _sinal(campo(col)) for rotulo, col in _TENDENCIAS},  # type: ignore[misc]
        forca_tendencia=_num(campo("ind_adx")),
        regioes=Regioes(
            resistencia=regiao("reg_res_dist", "reg_res_toques", 1),
            suporte=regiao("reg_sup_dist", "reg_sup_toques", -1),
        ),
        estrutura=Estrutura(
            ultimo_evento=_ultimo_evento(snapshot),
            topo=preco_a(campo("est_dist_topo")),
            fundo=preco_a(-campo("est_dist_fundo")),
        ),
        volume=VolumeAnalise(
            relativo=_num(campo("vol_relativo")),
            pressao_compradora=_num(campo("vol_pressao")),
        ),
        indicadores=Indicadores(
            rsi=_num(campo("ind_rsi")),
            macd_hist=_num(campo("ind_macd_hist") * atr, casas_preco + 2) if atr_ok else None,
            estoc_k=_num(campo("ind_estoc_k")),
            bb_pct=_num(campo("ind_bb_pct")),
            atr=_num(atr, casas_preco + 2) if atr_ok else None,
        ),
        price_action=PriceAction(
            impulso=_num(campo("pa_impulso")),
            desaceleracao=_num(campo("pa_desaceleracao")),
            lateral=campo("pa_lateral") == 1.0,
        ),
        resumo=[],
    )
    sem_dados = [rotulo for rotulo, col in _TENDENCIAS if not math.isfinite(campo(col))]
    return analise.model_copy(update={"resumo": montar_resumo(analise, sem_dados)})


# ------------------------------------------------------------------ resumo
def _fmt(x: float) -> str:
    texto = f"{x:.2f}".rstrip("0").rstrip(".")
    return texto.replace(".", ",")


def _lista(itens: Sequence[str]) -> str:
    return itens[0] if len(itens) == 1 else ", ".join(itens[:-1]) + " e " + itens[-1]


def _vezes(n: int) -> str:
    return f"{n} vez" if n == 1 else f"{n} vezes"


_EVENTOS = {
    "BOS_ALTA": "Rompimento de estrutura para cima (BOS de alta)",
    "BOS_BAIXA": "Rompimento de estrutura para baixo (BOS de baixa)",
    "CHOCH_ALTA": "Mudança de caráter para alta (CHoCH)",
    "CHOCH_BAIXA": "Mudança de caráter para baixa (CHoCH)",
}


def montar_resumo(a: Analise, sem_dados: Sequence[str] = ()) -> list[str]:
    """Frases curtas por template. Todo número do texto é um campo da própria ``Analise``.

    ``sem_dados``: tempos gráficos sem histórico para a tendência (no contrato saem 0); o texto
    diz "sem dados" em vez de afirmar que não há tendência."""
    frases: list[str] = []
    alta = [tg for tg, v in a.tendencia.items() if v == 1 and tg not in sem_dados]
    baixa = [tg for tg, v in a.tendencia.items() if v == -1 and tg not in sem_dados]
    neutra = [tg for tg, v in a.tendencia.items() if v == 0 and tg not in sem_dados]
    if alta:
        frases.append(f"Tendência de alta em {_lista(alta)}")
    if baixa:
        frases.append(f"Tendência de baixa em {_lista(baixa)}")
    if neutra:
        frases.append(f"Sem tendência definida em {_lista(neutra)}")
    if sem_dados:
        frases.append(f"Sem dados de tendência em {_lista(list(sem_dados))}")
    adx = a.forca_tendencia
    if adx is not None and adx >= 25:
        frases.append(f"Tendência forte (ADX {_fmt(adx)})")
    elif adx is not None and adx < 20:
        frases.append(f"Tendência fraca (ADX {_fmt(adx)})")
    if a.regioes.resistencia is not None:
        r = a.regioes.resistencia
        if r.distancia_atr > 0:
            frases.append(
                f"Preço a {_fmt(r.distancia_atr)} ATR de uma resistência tocada {_vezes(r.toques)}"
            )
        else:
            frases.append(f"Preço sobre uma resistência tocada {_vezes(r.toques)}")
    if a.regioes.suporte is not None:
        s = a.regioes.suporte
        if s.distancia_atr > 0:
            frases.append(
                f"Preço a {_fmt(s.distancia_atr)} ATR de um suporte tocado {_vezes(s.toques)}"
            )
        else:
            frases.append(f"Preço sobre um suporte tocado {_vezes(s.toques)}")
    if a.estrutura.ultimo_evento is not None:
        frases.append(_EVENTOS[a.estrutura.ultimo_evento])
    rsi = a.indicadores.rsi
    if rsi is not None and rsi >= 70:
        frases.append(f"RSI em {_fmt(rsi)}: região de sobrecompra")
    elif rsi is not None and rsi <= 30:
        frases.append(f"RSI em {_fmt(rsi)}: região de sobrevenda")
    rel = a.volume.relativo
    if rel is not None and rel >= 1.5:
        frases.append(f"Volume {_fmt(rel)} vez a média recente")
    elif rel is not None and rel <= 0.5:
        frases.append(f"Volume baixo: {_fmt(rel)} da média recente")
    pressao = a.volume.pressao_compradora
    if pressao is not None and pressao >= 0.3:
        frases.append(f"Agressão compradora predominante ({_fmt(pressao)})")
    elif pressao is not None and pressao <= -0.3:
        frases.append(f"Agressão vendedora predominante ({_fmt(abs(pressao))})")
    pa = a.price_action
    if pa.lateral:
        frases.append("Mercado lateral")
    if pa.impulso is not None and pa.desaceleracao is not None and pa.desaceleracao < 0:
        frases.append("Movimento perdendo força (desaceleração)")
    return frases


# ------------------------------------------------------------- motor ao vivo
MAXIMO_ENTREGAS = 5
STREAM_MORTOS = "candle.fechado.mortos"
# Pendente sem ACK há mais que isto (de qualquer réplica, viva ou morta) é tomado de novo.
MIN_OCIOSO_MS = 60_000


@dataclass(frozen=True, slots=True)
class ResultadoLote:
    publicadas: int
    descartadas: list[str]
    falhas: list[str]


def decidir_pendentes(
    pendentes: Sequence[tuple[str, int]], maximo: int = MAXIMO_ENTREGAS
) -> tuple[list[str], list[str]]:
    """(ids para tentar de novo, ids que já foram entregues ``maximo`` vezes: fila morta)."""
    reprocessar = [i for i, n in pendentes if n < maximo]
    desistir = [i for i, n in pendentes if n >= maximo]
    return reprocessar, desistir


def nome_consumidor(env: Mapping[str, str]) -> str:
    """Nome estável por réplica: ``SINAIS_CONSUMIDOR`` ou o nome do host do contêiner."""
    return env.get("SINAIS_CONSUMIDOR") or f"motor-{socket.gethostname()}"


type Concluir = Callable[[list[tuple[str, dict[str, str]]]], Awaitable[None]]


async def revisar_pendentes(
    redis: Any,
    consumidor: str,
    concluir: Concluir,
    min_ocioso_ms: int = MIN_OCIOSO_MS,
    stream: str = STREAM_CANDLE_FECHADO,
    grupo: str = GRUPO,
    mortos: str = STREAM_MORTOS,
) -> int:
    """Pendentes sem ACK de **qualquer** consumidor do grupo ociosos há ``min_ocioso_ms``: os
    que já foram entregues ``MAXIMO_ENTREGAS`` vezes vão para a fila morta; os outros são
    tomados por este consumidor com ``XAUTOCLAIM`` (uma réplica que morreu não deixa eventos
    presos) e processados de novo por ``concluir``. Devolve quantos foram reprocessados."""
    pend = await redis.xpending_range(
        stream, grupo, min="-", max="+", count=500, idle=min_ocioso_ms
    )
    _, desistir = decidir_pendentes([(p["message_id"], int(p["times_delivered"])) for p in pend])
    for id_ in desistir:
        for i, campos in await redis.xrange(stream, id_, id_):
            await redis.xadd(mortos, {**campos, "id_original": i}, maxlen=10_000)
        await redis.xack(stream, grupo, id_)
        _log.error("motor_analise.fila_morta", extra={"campos": {"id": id_}})
    reprocessados = 0
    inicio = "0-0"
    for _ in range(100):  # no máximo 50 mil por revisão; o resto fica para a próxima
        resposta = await redis.xautoclaim(
            stream, grupo, consumidor, min_idle_time=min_ocioso_ms, start_id=inicio, count=500
        )
        proximo, entradas = resposta[0], resposta[1]
        validas = [(i, c) for i, c in entradas if c]
        if validas:
            await concluir(validas)
            reprocessados += len(validas)
        if str(proximo) == "0-0":
            break
        inicio = proximo
    return reprocessados


class MotorAnalise:
    def __init__(
        self,
        simbolos: Sequence[str],
        repo: RepositorioCandles,
        armazem: ArmazemAnalises,
        publicador: Publicador,
        janela_min: int = JANELA_AO_VIVO_1M,
    ) -> None:
        self._repo = repo
        self._armazem = armazem
        self._pub = publicador
        self._janela_min = janela_min
        self._janelas: dict[str, deque[Candle]] = {s: deque(maxlen=janela_min) for s in simbolos}

    def janela(self, simbolo: str) -> list[Candle]:
        return list(self._janelas[simbolo])

    def ultima_abertura(self, simbolo: str) -> int | None:
        j = self._janelas[simbolo]
        return j[-1].abertura if j else None

    async def carregar(self, agora_ms: int) -> None:
        """Carrega do banco os últimos ``janela_min`` minutos fechados até ``agora_ms``."""
        fim = agora_ms - agora_ms % _M
        for simbolo, janela in self._janelas.items():
            janela.clear()
            janela.extend(
                await self._repo.listar(
                    simbolo, IntervaloColeta.M1, fim - self._janela_min * _M, fim
                )
            )
            _log.info(
                "motor_analise.carregado", extra={"campos": {"simbolo": simbolo, "n": len(janela)}}
            )

    async def _novos(self, simbolo: str, ate_abertura: int) -> list[Candle]:
        """Lê do banco (fonte da verdade, com o volume agressor) o que falta até
        ``ate_abertura``, sem mexer na janela."""
        janela = self._janelas[simbolo]
        fim = ate_abertura + _M
        inicio = janela[-1].abertura + _M if janela else fim - self._janela_min * _M
        inicio = max(inicio, fim - self._janela_min * _M)
        return await self._repo.listar(simbolo, IntervaloColeta.M1, inicio, fim)

    async def processar_lote(self, eventos: Sequence[Mapping[str, str]]) -> int:
        """Atalho para testes e para o carregamento: devolve quantas análises publicou."""
        r = await self.processar_entradas([(str(i), ev) for i, ev in enumerate(eventos)])
        return r.publicadas

    async def processar_entradas(
        self, entradas: Sequence[tuple[str, Mapping[str, str]]]
    ) -> ResultadoLote:
        """Processa entradas ``(id, campos)`` de ``candle.fechado``; calcula uma vez por
        símbolo. Evento malformado vai para ``descartadas`` (nunca melhora: ACK e fila morta);
        falha de cálculo deixa só os eventos daquele símbolo em ``falhas`` (nova tentativa)."""
        alvo: dict[str, int] = {}
        ids: dict[str, list[str]] = {}
        descartadas: list[str] = []
        for id_, ev in entradas:
            if ev.get("intervalo_ms") != str(_M):
                continue
            try:
                simbolo = ev["simbolo"]
                abertura = int(ev["abertura"])
            except (KeyError, TypeError, ValueError):
                descartadas.append(id_)
                _log.error("motor_analise.evento_invalido", extra={"campos": {"id": id_}})
                continue
            if simbolo not in self._janelas:
                continue
            ultima = self.ultima_abertura(simbolo)
            if ultima is not None and abertura <= ultima:
                continue
            alvo[simbolo] = max(abertura, alvo.get(simbolo, abertura))
            ids.setdefault(simbolo, []).append(id_)
        publicadas = 0
        falhas: list[str] = []
        for simbolo, abertura in alvo.items():
            try:
                publicadas += await self._publicar(simbolo, abertura)
            except Exception as erro:
                falhas.extend(ids[simbolo])
                _log.error(
                    "motor_analise.calculo_falhou",
                    extra={"campos": {"simbolo": simbolo, "erro": type(erro).__name__}},
                )
        return ResultadoLote(publicadas, descartadas, falhas)

    async def _publicar(self, simbolo: str, abertura: int) -> int:
        """Calcula com a janela + os minutos novos e só então avança a janela: se o cálculo,
        a gravação ou a publicação falhar, a nova tentativa do mesmo evento recalcula (antes
        ela era ignorada como repetida e a análise ficava parada)."""
        novos = await self._novos(simbolo, abertura)
        if not novos:
            return 0
        janela = self._janelas[simbolo]
        velas = [*janela, *novos][-self._janela_min :]
        analise = await asyncio.to_thread(self.calcular, simbolo, velas)
        if analise is not None:
            texto = analise.model_dump_json()
            await self._armazem.salvar(simbolo, texto)
            await self._pub.publicar(
                STREAM_ANALISE_ATUALIZADA, evento_analise_atualizada(simbolo, analise.t, texto)
            )
        janela.extend(novos)
        return 0 if analise is None else 1

    def calcular(self, simbolo: str, velas: Sequence[Candle] | None = None) -> Analise | None:
        """Análise da janela de ``simbolo`` (ou de ``velas``, quando informadas)."""
        lista = list(velas) if velas is not None else self.janela(simbolo)
        if not lista:
            return None
        snapshot = montar_snapshot(para_quadro(lista))
        return montar_analise(simbolo, snapshot, decimal_texto(lista[-1].fechamento))


async def principal() -> None:  # pragma: no cover - ligação de I/O
    from redis.asyncio import Redis
    from redis.exceptions import ResponseError
    from sqlalchemy.ext.asyncio import create_async_engine

    from sinais.core.config import carregar_configuracao
    from sinais.core.dominio import ATIVOS_V1
    from sinais.core.tempo import RelogioSistema
    from sinais.eventos.redis_streams import PublicadorRedis
    from sinais.logs import configurar_logs
    from sinais.persistencia.analises import ArmazemAnalisesRedis
    from sinais.persistencia.repositorio_pg import RepositorioCandlesPg
    from sinais.persistencia.url import url_async

    cfg = carregar_configuracao()
    configurar_logs(cfg.nivel_log)
    engine = create_async_engine(url_async(cfg.database_url.get_secret_value()))
    redis = Redis.from_url(cfg.redis_url.get_secret_value(), decode_responses=True)
    parar = asyncio.Event()
    laco = asyncio.get_running_loop()
    for sinal in (signal.SIGTERM, signal.SIGINT):
        laco.add_signal_handler(sinal, parar.set)
    # O grupo nasce antes da carga do banco: o que fechar durante a carga fica na fila.
    try:
        await redis.xgroup_create(STREAM_CANDLE_FECHADO, GRUPO, id="$", mkstream=True)
    except ResponseError as erro:
        if "BUSYGROUP" not in str(erro):
            raise
    motor = MotorAnalise(
        [a.simbolo for a in ATIVOS_V1],
        RepositorioCandlesPg(engine),
        ArmazemAnalisesRedis(redis),
        PublicadorRedis(redis),
    )
    await motor.carregar(RelogioSistema().agora_ms())
    armazem, publicador = ArmazemAnalisesRedis(redis), PublicadorRedis(redis)
    for simbolo in (a.simbolo for a in ATIVOS_V1):
        analise = await asyncio.to_thread(motor.calcular, simbolo)
        if analise is not None:
            texto = analise.model_dump_json()
            await armazem.salvar(simbolo, texto)
            await publicador.publicar(
                STREAM_ANALISE_ATUALIZADA, evento_analise_atualizada(simbolo, analise.t, texto)
            )
    consumidor = nome_consumidor(os.environ)
    _log.info("motor_analise.iniciado", extra={"campos": {"consumidor": consumidor}})

    async def concluir(entradas: list[tuple[str, dict[str, str]]]) -> None:
        r = await motor.processar_entradas(entradas)
        for id_ in r.descartadas:
            campos = next(c for i, c in entradas if i == id_)
            morto: dict[Any, Any] = {**campos, "id_original": id_}
            await redis.xadd(STREAM_MORTOS, morto, maxlen=10_000)
        ok = [i for i, _ in entradas if i not in set(r.falhas)]
        if ok:
            await redis.xack(STREAM_CANDLE_FECHADO, GRUPO, *ok)
        if r.publicadas:
            _log.info("motor_analise.publicado", extra={"campos": {"analises": r.publicadas}})

    proxima_revisao = 0.0
    while not parar.is_set():
        try:
            if laco.time() >= proxima_revisao:
                await revisar_pendentes(redis, consumidor, concluir)
                proxima_revisao = laco.time() + 30
            resposta = await redis.xreadgroup(
                GRUPO, consumidor, {STREAM_CANDLE_FECHADO: ">"}, count=500, block=2000
            )
            entradas = [(i, c) for _, lista in resposta or [] for i, c in lista]
            if entradas:
                await concluir(entradas)
        except Exception as erro:
            _log.error("motor_analise.laco_falhou", extra={"campos": {"erro": repr(erro)}})
            await asyncio.sleep(1)
    await redis.aclose()
    await engine.dispose()


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(principal())
