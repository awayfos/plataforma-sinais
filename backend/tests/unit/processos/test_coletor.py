import asyncio
import json

from sinais.core.tempo import RelogioFixo
from sinais.dados.modelos import IntervaloColeta
from sinais.eventos.contratos import STREAM_CANDLE_FECHADO
from sinais.eventos.memoria import PublicadorMemoria
from sinais.persistencia.memoria import RepositorioCandlesMemoria
from sinais.processos.coletor_binance import Coletor

from ..dados.fonte_falsa import FonteFalsa

T0 = 1795575600000  # alinhado a 5m
M = 60_000
D = 86_400_000
M1 = IntervaloColeta.M1


def msg(t: int, fechado: bool = True, intervalo: str = "1m") -> str:
    k = {
        "t": t,
        "T": t + 59_999,
        "s": "BTCUSDT",
        "i": intervalo,
        "o": "100",
        "c": "101",
        "h": "102",
        "l": "99",
        "v": "1",
        "n": 3,
        "x": fechado,
        "q": "100",
        "V": "0.5",
    }
    return json.dumps(
        {
            "stream": "btcusdt@kline_1m",
            "data": {"e": "kline", "E": t + 60_001, "s": "BTCUSDT", "k": k},
        }
    )


def montar(
    agora: int, historico_dias: int = 1
) -> tuple[Coletor, FonteFalsa, RepositorioCandlesMemoria, PublicadorMemoria, RelogioFixo]:
    fonte, repo, pub, rel = (
        FonteFalsa(),
        RepositorioCandlesMemoria(),
        PublicadorMemoria(),
        RelogioFixo(agora),
    )
    c = Coletor(
        ["BTCUSDT"], [M1], fonte, repo, pub, rel, historico_dias=historico_dias, historico_dias_1s=1
    )
    return c, fonte, repo, pub, rel


def aberturas(pub: PublicadorMemoria, intervalo_ms: int = M) -> list[int]:
    return [
        int(e["abertura"])
        for s, e in pub.publicados
        if s == STREAM_CANDLE_FECHADO and int(e["intervalo_ms"]) == intervalo_ms
    ]


def test_sincronizar_inicial_usa_historico_dias() -> None:
    agora = T0 + 30_000
    c, fonte, repo, _, _ = montar(agora, historico_dias=2)
    asyncio.run(c.sincronizar())
    [(_, _, inicio, fim)] = fonte.chamadas[:1]
    assert inicio == T0 - 2 * D
    assert asyncio.run(repo.ultima_abertura("BTCUSDT", M1)) == T0 - M


def test_sincronizar_continua_do_ultimo() -> None:
    c, fonte, repo, _, rel = montar(T0 + 30_000)
    asyncio.run(c.sincronizar())
    fonte.chamadas.clear()
    rel.definir(T0 + 5 * M + 1)
    asyncio.run(c.sincronizar())
    assert fonte.chamadas == [("BTCUSDT", "1m", T0, T0 + 5 * M)]


def test_mensagem_em_formacao_ignorada() -> None:
    c, _, repo, pub, _ = montar(T0)
    asyncio.run(c.ao_mensagem(msg(T0, fechado=False)))
    assert pub.publicados == []
    assert asyncio.run(repo.ultima_abertura("BTCUSDT", M1)) is None


def test_mensagem_fechada_grava_e_publica() -> None:
    c, _, repo, pub, _ = montar(T0)
    asyncio.run(c.ao_mensagem(msg(T0)))
    assert aberturas(pub) == [T0]
    assert asyncio.run(repo.ultima_abertura("BTCUSDT", M1)) == T0


def test_duplicada_nao_publica_de_novo() -> None:
    c, _, _, pub, _ = montar(T0)
    asyncio.run(c.ao_mensagem(msg(T0)))
    asyncio.run(c.ao_mensagem(msg(T0)))
    assert aberturas(pub) == [T0]


def test_mensagem_invalida_nao_derruba() -> None:
    c, _, _, pub, _ = montar(T0)
    asyncio.run(c.ao_mensagem("{lixo"))
    assert pub.publicados == []


def test_reconectar_preenche_lacuna_antes_de_publicar() -> None:
    c, _, _, pub, rel = montar(T0)
    asyncio.run(c.ao_mensagem(msg(T0)))
    rel.definir(T0 + 4 * M + 10)
    asyncio.run(c.ao_reconectar())
    asyncio.run(c.ao_mensagem(msg(T0 + 4 * M)))
    assert aberturas(pub) == [T0, T0 + M, T0 + 2 * M, T0 + 3 * M, T0 + 4 * M]


def test_publica_5m_quando_bloco_completa() -> None:
    c, _, _, pub, _ = montar(T0)
    for i in range(5):
        asyncio.run(c.ao_mensagem(msg(T0 + i * M)))
    assert aberturas(pub, 5 * M) == [T0]
