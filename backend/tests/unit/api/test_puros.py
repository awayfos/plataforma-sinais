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


def test_origem_permitida() -> None:
    assert origem_permitida(None, "api:8000", ())
    assert origem_permitida("https://app.exemplo.com", "app.exemplo.com", ())
    assert origem_permitida(
        "https://painel.exemplo.com", "api:8000", ("https://painel.exemplo.com",)
    )
    assert not origem_permitida("https://malicioso.com", "app.exemplo.com", ())
    assert not origem_permitida("null", "app.exemplo.com", ())


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


def test_ip_do_cliente_usa_a_ultima_entrada_do_proxy_confiavel() -> None:
    from sinais.api.ws_canais import ip_do_cliente

    assert ip_do_cliente("10.0.0.5", None, confiar_proxy=False) == "10.0.0.5"
    assert ip_do_cliente("10.0.0.5", "6.6.6.6", confiar_proxy=False) == "10.0.0.5"
    # o cliente pode forjar o início da lista; o proxy acrescenta o IP real no fim
    assert ip_do_cliente("10.0.0.5", "6.6.6.6, 203.0.113.9", confiar_proxy=True) == "203.0.113.9"
    assert ip_do_cliente("10.0.0.5", " ", confiar_proxy=True) == "10.0.0.5"
    assert ip_do_cliente(None, None, confiar_proxy=True) == "desconhecido"
    assert len(ip_do_cliente("x" * 100, None, confiar_proxy=False)) == 64


def test_acesso_auditoria_qualidade_com_campos_do_frontend() -> None:
    from sinais.api.visoes import acesso_saida, auditoria_saida, qualidade_saida
    from sinais.contas.modelos import RegistroAcesso, RegistroAuditoria

    a = acesso_saida(RegistroAcesso(5, 1, "login", "1.2.3.4", "ua", T0), "a@b.com")
    assert a.model_dump() == {
        "id": 5,
        "usuario_id": 1,
        "email": "a@b.com",
        "evento": "login",
        "ip": "1.2.3.4",
        "user_agent": "ua",
        "t": T0,
        "ts": T0,
    }
    r = auditoria_saida(
        RegistroAuditoria(7, 2, "plano.criar", "plano:1", None, {"x": 1}, T0), "adm@b.com"
    )
    assert r.model_dump() == {
        "id": 7,
        "admin_id": 2,
        "admin_email": "adm@b.com",
        "acao": "plano.criar",
        "alvo": "plano:1",
        "antes": None,
        "depois": {"x": 1},
        "t": T0,
        "ts": T0,
    }
    q = qualidade_saida(("BTCUSDT", "1m", T0, T0 + 60_000, "lacuna"))
    assert q.model_dump() == {
        "simbolo": "BTCUSDT",
        "intervalo": "1m",
        "inicio": T0,
        "fim": T0 + 60_000,
        "tipo": "lacuna",
        "detalhes": None,
    }


def test_sinal_tem_tolerancia_e_preco_de_referencia_nulos_em_aguardar() -> None:
    s = sinais_para("BTCUSDT", ("1m",), lambda s, e: None)[0].model_dump()
    assert s["tolerancia_preco"] is None and s["preco_referencia"] is None
