"""Conversão do domínio para os esquemas do contrato."""

from __future__ import annotations

from sinais.api import esquemas as e
from sinais.contas.admin import FichaUsuario
from sinais.contas.contexto import status_assinatura
from sinais.contas.modelos import (
    Assinatura,
    ItemPayout,
    Plano,
    Recursos,
    RegistroAcesso,
    RegistroAuditoria,
    Usuario,
)
from sinais.core.tempo import InstanteMs
from sinais.dados.modelos import Candle
from sinais.persistencia.repositorio import EventoQualidade


def usuario_saida(
    u: Usuario, a: Assinatura | None, p: Plano | None, agora: InstanteMs
) -> e.Usuario:
    return e.Usuario(
        id=u.id,
        email=u.email,
        nome=u.nome,
        papel=u.papel.value,
        modo=u.modo.value,
        layout=u.layout,
        assinatura=e.AssinaturaUsuario(
            plano=p.nome if p else None,
            status=status_assinatura(u, a, agora),
            vence_em=a.fim if a else None,
        ),
    )


def usuario_admin(f: FichaUsuario, agora: InstanteMs) -> e.UsuarioAdmin:
    base = usuario_saida(f.usuario, f.assinatura, f.plano, agora)
    return e.UsuarioAdmin(
        **base.model_dump(), status=f.usuario.status.value, criado_em=f.usuario.criado_em
    )


def recursos_de(r: e.RecursosPlano) -> Recursos:
    return Recursos(tuple(r.ativos), tuple(r.expiracoes), r.modo_avancado, r.cursos)


def plano_saida(p: Plano) -> e.Plano:
    return e.Plano(
        id=p.id,
        nome=p.nome,
        duracao_dias=p.duracao_dias,
        preco_centavos=p.preco_centavos,
        recursos=e.RecursosPlano(
            ativos=list(p.recursos.ativos),
            expiracoes=list(p.recursos.expiracoes),  # type: ignore[arg-type]
            modo_avancado=p.recursos.modo_avancado,
            cursos=p.recursos.cursos,
        ),
        ativo=p.ativo,
    )


def assinatura_saida(a: Assinatura) -> e.Assinatura:
    return e.Assinatura(
        id=a.id,
        usuario_id=a.usuario_id,
        plano_id=a.plano_id,
        inicio=a.inicio,
        fim=a.fim,
        origem=a.origem,
    )


def acesso_saida(r: RegistroAcesso, email: str | None) -> e.Acesso:
    return e.Acesso(
        id=r.id,
        usuario_id=r.usuario_id,
        email=email,
        evento=r.evento,
        ip=r.ip,
        user_agent=r.user_agent,
        t=r.t,
        ts=r.t,
    )


def auditoria_saida(r: RegistroAuditoria, admin_email: str | None) -> e.RegistroAuditoria:
    return e.RegistroAuditoria(
        id=r.id,
        admin_id=r.admin_id,
        admin_email=admin_email,
        acao=r.acao,
        alvo=r.alvo,
        antes=r.antes,
        depois=r.depois,
        t=r.t,
        ts=r.t,
    )


def payout_saida(i: ItemPayout) -> e.Payout:
    return e.Payout(simbolo=i.simbolo, expiracao=i.expiracao, payout=i.payout)  # type: ignore[arg-type]


def qualidade_saida(q: EventoQualidade) -> e.EventoQualidade:
    simbolo, intervalo, inicio, fim, tipo = q
    return e.EventoQualidade(
        simbolo=simbolo, intervalo=intervalo, inicio=inicio, fim=fim, tipo=tipo
    )


def candle_saida(c: Candle) -> e.CandleSaida:
    return e.CandleSaida(
        t=c.abertura,
        o=e.decimal_texto(c.abertura_preco),
        h=e.decimal_texto(c.maxima),
        l=e.decimal_texto(c.minima),
        c=e.decimal_texto(c.fechamento),
        v=e.decimal_texto(c.volume),
    )
