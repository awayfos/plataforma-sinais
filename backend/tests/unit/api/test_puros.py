"""Partes puras da API: visões, sinais sem modelo, canais do WebSocket e distribuidor."""

import asyncio
import json

import pytest

from sinais.api.sinais_ao_vivo import (
    EXPIRACOES,
    MOTIVO_SEM_MODELO,
    MOTIVO_SEM_MOTOR,
    sinais_para,
)
from sinais.api.visoes import candle_saida, usuario_saida
from sinais.api.ws_canais import (
    Canal,
    Distribuidor,
    ErroMensagem,
    interpretar,
    origem_permitida,
    traduzir_evento,
)
from sinais.contas.modelos import Assinatura, Modo, Papel, Plano, Recursos, StatusUsuario, Usuario
from sinais.eventos.contratos import evento_analise_atualizada, evento_candle_fechado

from ..eventos.test_contratos import vela

T0 = 1795575600000
D = 86_400_000


def _usuario(status: StatusUsuario = StatusUsuario.ATIVO) -> Usuario:
    return Usuario(
        1,
        "a@b.com",
        "Ana",
        Papel.CLIENTE,
        status,
        "h",
        None,
        None,
        Modo.AVANCADO,
        {"BTCUSDT": {"linhas": [1]}},
        T0,
    )


def test_usuario_saida_com_e_sem_assinatura() -> None:
    p = Plano(3, "Mensal", 30, 9900, Recursos(("BTCUSDT",), ("1m",), True, False), True)
    a = Assinatura(9, 1, 3, T0, T0 + D, "manual", T0)
    saida = usuario_saida(_usuario(), a, p, T0 + 1)
    assert saida.model_dump() == {
        "id": 1,
        "email": "a@b.com",
        "nome": "Ana",
        "papel": "cliente",
        "modo": "avancado",
        "layout": {"BTCUSDT": {"linhas": [1]}},
        "assinatura": {"plano": "Mensal", "status": "ativa", "vence_em": T0 + D},
    }
    assert usuario_saida(_usuario(), a, p, T0 + D).assinatura.status == "vencida"
    vazia = usuario_saida(_usuario(), None, None, T0).assinatura
    assert (vazia.plano, vazia.status, vazia.vence_em) == (None, "vencida", None)


def test_candle_saida_precos_em_texto_exato() -> None:
    c = candle_saida(vela())
    assert c.model_dump() == {
        "t": T0,
        "o": "59194.01",
        "h": "59200.5",
        "l": "59190",
        "c": "59199.99",
        "v": "1.23456789",
    }


def test_sinais_sem_campeao_aguardam_em_todas_as_expiracoes() -> None:
    lista = sinais_para("BTCUSDT", EXPIRACOES, lambda s, e: None)
    assert [s.expiracao for s in lista] == ["1m", "5m", "15m", "30m", "60m"]
    for s in lista:
        assert s.direcao == "AGUARDAR" and s.probabilidade is None
        assert s.motivo == MOTIVO_SEM_MODELO == "Nenhum modelo validado para esta expiração"
        assert (s.n_validacao, s.janela_ate, s.invalidacao, s.modelo) == (None, None, None, None)


def test_sinais_com_campeao_ainda_aguardam_sem_motor() -> None:
    lista = sinais_para("BTCUSDT", ("1m", "5m"), lambda s, e: "v7" if e == "1m" else None)
    assert (lista[0].direcao, lista[0].motivo, lista[0].modelo) == (
        "AGUARDAR",
        MOTIVO_SEM_MOTOR,
        "v7",
    )
    assert lista[1].motivo == MOTIVO_SEM_MODELO


@pytest.mark.parametrize(
    ("texto", "acao", "canal"),
    [
        (
            '{"acao": "assinar", "canal": "candles:BTCUSDT:1m"}',
            "assinar",
            Canal("candles", "BTCUSDT", "1m"),
        ),
        (
            '{"acao": "cancelar", "canal": "analise:ETHUSDT"}',
            "cancelar",
            Canal("analise", "ETHUSDT", None),
        ),
        (
            '{"acao": "assinar", "canal": "sinais:BTCUSDT"}',
            "assinar",
            Canal("sinais", "BTCUSDT", None),
        ),
    ],
)
def test_interpretar_mensagens_validas(texto: str, acao: str, canal: Canal) -> None:
    assert interpretar(texto, ("BTCUSDT", "ETHUSDT")) == (acao, canal)
    assert canal.nome == json.loads(texto)["canal"]


@pytest.mark.parametrize(
    "texto",
    [
        "não é json",
        "[]",
        '{"acao": "apagar", "canal": "analise:BTCUSDT"}',
        '{"acao": "assinar"}',
        '{"acao": "assinar", "canal": "candles:BTCUSDT:2m"}',
        '{"acao": "assinar", "canal": "candles:BTCUSDT"}',
        '{"acao": "assinar", "canal": "analise:XRPUSDT"}',
        '{"acao": "assinar", "canal": "grafico:BTCUSDT:1m"}',
        '{"acao": "assinar", "canal": "analise:BTCUSDT:1m"}',
        "x" * 5000,
    ],
)
def test_interpretar_recusa_mensagens_invalidas(texto: str) -> None:
    with pytest.raises(ErroMensagem):
        interpretar(texto, ("BTCUSDT", "ETHUSDT"))


def test_origem_permitida_so_pela_lista_ou_host_encaminhado_de_proxy_confiavel() -> None:
    lista = ("http://localhost:3000",)
    assert origem_permitida(None, lista)  # cliente que não é navegador: o cookie decide
    assert origem_permitida("http://localhost:3000", lista)
    assert not origem_permitida("https://malicioso.com", lista)
    assert not origem_permitida("null", lista)
    # Host igual não basta mais: atrás do proxy o Host é interno
    assert not origem_permitida("https://app.exemplo.com", ())
    assert origem_permitida(
        "https://app.exemplo.com", (), host_encaminhado="app.exemplo.com", proxy_confiavel=True
    )
    assert not origem_permitida(
        "https://app.exemplo.com", (), host_encaminhado="app.exemplo.com", proxy_confiavel=False
    )


def test_distribuidor_entrega_por_canal_e_descarta_o_mais_antigo() -> None:
    async def caso() -> None:
        d = Distribuidor(tamanho_fila=2)
        a, b = d.novo_assinante(), d.novo_assinante()
        d.assinar(a, "analise:BTCUSDT")
        d.assinar(b, "analise:ETHUSDT")
        assert d.publicar("analise:BTCUSDT", {"n": 1}) == 1
        assert await a.fila.get() == {"canal": "analise:BTCUSDT", "dados": {"n": 1}}
        assert b.fila.empty()
        for n in range(3):
            d.publicar("analise:BTCUSDT", {"n": n})
        assert [(await a.fila.get())["dados"]["n"] for _ in range(2)] == [1, 2]
        d.cancelar(a, "analise:BTCUSDT")
        assert d.publicar("analise:BTCUSDT", {}) == 0
        d.assinar(b, "analise:BTCUSDT")
        d.remover(b)
        assert d.publicar("analise:BTCUSDT", {}) == 0
        assert d.publicar("analise:ETHUSDT", {}) == 0

    asyncio.run(caso())


def test_traduzir_candle_fechado_e_analise() -> None:
    ev = evento_candle_fechado(vela())
    assert traduzir_evento("candle.fechado", ev) == [
        (
            "candles:BTCUSDT:1m",
            {
                "t": T0,
                "o": "59194.01",
                "h": "59200.5",
                "l": "59190",
                "c": "59199.99",
                "v": "1.23456789",
                "fechado": True,
            },
        )
    ]
    assert traduzir_evento("candle.fechado", dict(ev, intervalo_ms="1000")) == []
    assert (
        traduzir_evento("candle.fechado", dict(ev, intervalo_ms="300000"))[0][0]
        == "candles:BTCUSDT:5m"
    )
    an = evento_analise_atualizada("ETHUSDT", T0, '{"simbolo": "ETHUSDT", "t": 1}')
    canais = traduzir_evento("analise.atualizada", an)
    assert canais[0] == ("analise:ETHUSDT", {"simbolo": "ETHUSDT", "t": 1})
    assert canais[1][0] == "sinais:ETHUSDT"
    assert [s["expiracao"] for s in canais[1][1]] == list(EXPIRACOES)
    assert traduzir_evento("outro", {}) == []
    assert traduzir_evento("candle.fechado", {"lixo": "1"}) == []
    assert canais[0][1]["t"] == 1


def test_ip_do_cliente_anda_no_x_forwarded_for_da_direita_pulando_proxies_confiaveis() -> None:
    from ipaddress import ip_network

    from sinais.api.ws_canais import ip_do_cliente

    proxies = (ip_network("127.0.0.1/32"), ip_network("172.16.0.0/12"))
    # conexão direta de fora: XFF é ignorado (pode ser forjado)
    assert ip_do_cliente("203.0.113.9", "1.1.1.1", proxies) == "203.0.113.9"
    # Next (172.18.0.3) → nginx (127.0.0.1) → API: o primeiro de fora, vindo da direita
    xff = "6.6.6.6, 198.51.100.7, 172.18.0.3"
    assert ip_do_cliente("127.0.0.1", xff, proxies) == "198.51.100.7"
    assert ip_do_cliente("127.0.0.1", None, proxies) == "127.0.0.1"
    assert ip_do_cliente("127.0.0.1", "172.18.0.3", proxies) == "172.18.0.3"
    assert ip_do_cliente("127.0.0.1", "lixo, 172.18.0.3", proxies) == "lixo"
    assert ip_do_cliente(None, None, proxies) == "desconhecido"
    assert ip_do_cliente("10.0.0.5", "6.6.6.6", ()) == "10.0.0.5"
    assert len(ip_do_cliente("x" * 100, None, ())) == 64


def test_campeao_malformado_cai_para_aguardar(tmp_path: object) -> None:
    from pathlib import Path

    from sinais.api.sinais_ao_vivo import campeao_do_registro

    pasta = Path(str(tmp_path))
    for simbolo, conteudo in (("BTCUSDT", "[1, 2]"), ("ETHUSDT", "{nao e json")):
        d = pasta / simbolo / "1m"
        d.mkdir(parents=True)
        (d / "campeao.json").write_text(conteudo)
    (pasta / "BTCUSDT" / "5m").mkdir(parents=True)
    (pasta / "BTCUSDT" / "5m" / "campeao.json").write_text('{"versao": "v3"}')
    busca = campeao_do_registro(str(pasta))
    assert busca("BTCUSDT", "1m") is None
    assert busca("ETHUSDT", "1m") is None
    assert busca("BTCUSDT", "5m") == "v3"
    assert busca("BTCUSDT", "15m") is None


def test_supervisor_reinicia_a_fonte_de_eventos_que_morre() -> None:
    from sinais.api.supervisao import supervisionar

    chamadas: list[int] = []

    async def fonte() -> None:
        chamadas.append(1)
        if len(chamadas) == 1:
            raise RuntimeError("redis caiu")
        if len(chamadas) == 2:
            return  # terminou sem erro: também reinicia
        await asyncio.sleep(3600)

    async def caso() -> None:
        tarefa = asyncio.create_task(supervisionar("fonte", fonte, espera_s=0))
        for _ in range(50):
            await asyncio.sleep(0)
        tarefa.cancel()
        with pytest.raises(asyncio.CancelledError):
            await tarefa

    asyncio.run(caso())
    assert len(chamadas) == 3


def test_entrada_ruim_no_stream_nao_derruba_as_outras() -> None:
    from sinais.api.eventos_redis import distribuir_resposta

    d = Distribuidor()
    a = d.novo_assinante()
    d.assinar(a, "candles:BTCUSDT:1m")
    boa = evento_candle_fechado(vela())
    resposta = [
        (
            "candle.fechado",
            [("1-0", {"lixo": "x"}), ("2-0", dict(boa, o="nao-numero")), ("3-0", boa)],
        )
    ]
    ultimos = {"candle.fechado": "$"}
    assert distribuir_resposta(resposta, ultimos, d, None) == 1
    assert ultimos["candle.fechado"] == "3-0"
    assert a.fila.qsize() == 1


def test_ipv4_mapeado_em_ipv6_vale_como_ipv4_no_proxy_e_no_ip_do_cliente() -> None:
    from ipaddress import ip_network

    from sinais.api.ws_canais import de_proxy_confiavel, ip_do_cliente

    proxies = (ip_network("127.0.0.1/32"), ip_network("172.16.0.0/12"))
    # socket dual-stack: o nginx/Next local aparece como ::ffff:127.0.0.1
    assert de_proxy_confiavel("::ffff:127.0.0.1", proxies)
    assert de_proxy_confiavel("::ffff:172.18.0.3", proxies)
    assert not de_proxy_confiavel("::ffff:8.8.8.8", proxies)
    xff = "6.6.6.6, ::ffff:198.51.100.7, ::ffff:172.18.0.3"
    assert ip_do_cliente("::ffff:127.0.0.1", xff, proxies) == "198.51.100.7"
    # o mesmo cliente com e sem o prefixo cai no mesmo contador de limites
    assert ip_do_cliente("::ffff:203.0.113.9", None, ()) == "203.0.113.9"
    assert ip_do_cliente("2001:db8::1", None, ()) == "2001:db8::1"
