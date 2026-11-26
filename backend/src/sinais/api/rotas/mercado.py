"""Rotas de dados de mercado: exigem sessão, assinatura ativa e o ativo no plano."""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Query

from sinais.api import esquemas as e
from sinais.api.dependencias import Assinante, Svc
from sinais.api.erros import RESPOSTAS_ERRO
from sinais.api.servicos import NOMES_ATIVOS, Servicos
from sinais.api.sinais_ao_vivo import EXPIRACOES, sinais_para
from sinais.api.visoes import candle_saida
from sinais.contas.autorizacao import expiracoes_permitidas, pode_ver_ativo
from sinais.contas.contexto import Contexto
from sinais.contas.servico import ErroConta
from sinais.core.calendario import calendario_para
from sinais.core.dominio import TempoGrafico

rotas = APIRouter(prefix="/api", tags=["mercado"], responses=RESPOSTAS_ERRO)
LIMITE_CANDLES = 1500

Simbolo = Annotated[str, Query(min_length=1, max_length=32)]


def exigir_ativo(ctx: Contexto, s: Servicos, simbolo: str) -> str:
    if simbolo not in s.simbolos:
        raise ErroConta(404, "ativo_desconhecido", "Ativo não encontrado.")
    if not pode_ver_ativo(ctx, simbolo):
        raise ErroConta(403, "ativo_nao_incluido", "Este ativo não está incluído no seu plano.")
    return simbolo


@rotas.get("/ativos", response_model=list[e.Ativo])
async def ativos(ctx: Assinante, s: Svc) -> list[e.Ativo]:
    return [
        e.Ativo(
            simbolo=a.simbolo,
            nome=NOMES_ATIVOS.get(a.simbolo, a.simbolo),
            classe=a.classe.value,
            aberto=calendario_para(a).aberto(ctx.agora),
        )
        for a in s.ativos
        if pode_ver_ativo(ctx, a.simbolo)
    ]


@rotas.get("/candles", response_model=list[e.CandleSaida])
async def candles(
    ctx: Assinante,
    s: Svc,
    simbolo: Simbolo,
    tg: e.TempoGraficoRotulo = "1m",
    ate: Annotated[int | None, Query(ge=0)] = None,
    limite: Annotated[int, Query(ge=1, le=LIMITE_CANDLES)] = 500,
) -> list[e.CandleSaida]:
    exigir_ativo(ctx, s, simbolo)
    lista = await s.mercado.candles(
        simbolo, TempoGrafico(tg), ate if ate is not None else ctx.agora, limite, ctx.agora
    )
    return [candle_saida(c) for c in lista]


@rotas.get("/analise", response_model=e.Analise, responses={404: {"model": e.RespostaErro}})
async def analise(ctx: Assinante, s: Svc, simbolo: Simbolo) -> e.Analise:
    exigir_ativo(ctx, s, simbolo)
    texto = await s.analises.obter(simbolo)
    if texto is None:
        raise ErroConta(
            404, "analise_indisponivel", "Análise ainda não disponível para este ativo."
        )
    return e.Analise.model_validate(json.loads(texto))


@rotas.get("/sinais", response_model=list[e.Sinal])
async def sinais(ctx: Assinante, s: Svc, simbolo: Simbolo) -> list[e.Sinal]:
    exigir_ativo(ctx, s, simbolo)
    return sinais_para(simbolo, expiracoes_permitidas(ctx, EXPIRACOES), s.campeao)  # type: ignore[arg-type]


@rotas.get("/sinais/historico", response_model=list[e.SinalHistorico])
async def historico(
    ctx: Assinante,
    s: Svc,
    simbolo: Simbolo,
    inicio: Annotated[int | None, Query(ge=0)] = None,
    fim: Annotated[int | None, Query(ge=0)] = None,
) -> list[e.SinalHistorico]:
    """Sinais emitidos e liquidados. Vazio até o motor de sinais ao vivo gravar o primeiro."""
    exigir_ativo(ctx, s, simbolo)
    if inicio is not None and fim is not None and fim < inicio:
        raise ErroConta(422, "periodo_invalido", "O fim deve ser posterior ao início.")
    return []
