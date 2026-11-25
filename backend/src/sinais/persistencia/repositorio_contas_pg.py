"""Repositório de contas no PostgreSQL (mesmo contrato de ``RepositorioContasMemoria``)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

from sinais.contas.modelos import (
    Assinatura,
    ItemPayout,
    Modo,
    NovoPlano,
    NovoUsuario,
    Papel,
    Plano,
    Recursos,
    RegistroAcesso,
    RegistroAuditoria,
    Sessao,
    StatusUsuario,
    Usuario,
)
from sinais.contas.repositorio import ErroEmailDuplicado
from sinais.core.tempo import InstanteMs, de_datetime, para_datetime
from sinais.persistencia.tabelas_contas import (
    assinaturas,
    auditoria,
    configuracoes_usuario,
    corretora_ativos,
    corretora_payouts,
    corretoras,
    planos,
    registros_acesso,
    sessoes,
    usuarios,
)

EXPIRACAO_S = {"1m": 60, "5m": 300, "15m": 900, "30m": 1800, "60m": 3600}
ROTULO_EXPIRACAO = {v: k for k, v in EXPIRACAO_S.items()}


def _ms(dt: Any) -> InstanteMs | None:
    return None if dt is None else de_datetime(dt)


def _dt(ms: InstanteMs | None) -> Any:
    return None if ms is None else para_datetime(ms)


def _usuario(linha: Any) -> Usuario:
    return Usuario(
        id=int(linha.id),
        email=linha.email,
        nome=linha.nome,
        papel=Papel(linha.papel),
        status=StatusUsuario(linha.status),
        senha_hash=linha.senha_hash,
        totp_cifrado=linha.totp_cifrado,
        totp_ultimo_passo=None if linha.totp_ultimo_passo is None else int(linha.totp_ultimo_passo),
        modo=Modo(linha.modo or Modo.ESSENCIAL.value),
        layout=dict(linha.layout or {}),
        criado_em=de_datetime(linha.criado_em),
    )


def _sessao(linha: Any) -> Sessao:
    return Sessao(
        token_hash=linha.token_hash,
        csrf_hash=linha.csrf_hash,
        usuario_id=int(linha.usuario_id),
        criada_em=de_datetime(linha.criada_em),
        ultimo_uso=de_datetime(linha.ultimo_uso),
        expira_em=de_datetime(linha.expira_em),
        ip=linha.ip,
        user_agent=linha.user_agent,
        revogada_em=_ms(linha.revogada_em),
        motivo_revogacao=linha.motivo_revogacao,
    )


def _plano(linha: Any) -> Plano:
    r = linha.recursos
    return Plano(
        id=int(linha.id),
        nome=linha.nome,
        duracao_dias=int(linha.duracao_dias),
        preco_centavos=int(linha.preco_centavos),
        recursos=Recursos(
            ativos=tuple(r["ativos"]),
            expiracoes=tuple(r["expiracoes"]),
            modo_avancado=bool(r["modo_avancado"]),
            cursos=bool(r["cursos"]),
        ),
        ativo=bool(linha.ativo),
    )


def _recursos_json(r: Recursos) -> dict[str, Any]:
    return {
        "ativos": list(r.ativos),
        "expiracoes": list(r.expiracoes),
        "modo_avancado": r.modo_avancado,
        "cursos": r.cursos,
    }


def _assinatura(linha: Any) -> Assinatura:
    return Assinatura(
        id=int(linha.id),
        usuario_id=int(linha.usuario_id),
        plano_id=int(linha.plano_id),
        inicio=de_datetime(linha.inicio),
        fim=de_datetime(linha.fim),
        origem=linha.origem,
        criado_em=de_datetime(linha.criado_em),
    )


def _sessao_valores(s: Sessao) -> dict[str, Any]:
    return {
        "token_hash": s.token_hash,
        "csrf_hash": s.csrf_hash,
        "usuario_id": s.usuario_id,
        "criada_em": _dt(s.criada_em),
        "ultimo_uso": _dt(s.ultimo_uso),
        "expira_em": _dt(s.expira_em),
        "ip": s.ip,
        "user_agent": s.user_agent,
        "revogada_em": _dt(s.revogada_em),
        "motivo_revogacao": s.motivo_revogacao,
    }


def _escapar_like(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


_SELECAO_USUARIO = select(
    usuarios, configuracoes_usuario.c.modo, configuracoes_usuario.c.layout
).select_from(
    usuarios.outerjoin(configuracoes_usuario, configuracoes_usuario.c.usuario_id == usuarios.c.id)
)


class RepositorioContasPg:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    # -------------------------------------------------------------- usuários
    async def criar_usuario(self, novo: NovoUsuario) -> Usuario:
        try:
            async with self._engine.begin() as conn:
                uid = await conn.scalar(
                    usuarios.insert()
                    .values(
                        email=novo.email,
                        nome=novo.nome,
                        papel=novo.papel.value,
                        status=StatusUsuario.ATIVO.value,
                        senha_hash=novo.senha_hash,
                        totp_cifrado=novo.totp_cifrado,
                        criado_em=_dt(novo.criado_em),
                    )
                    .returning(usuarios.c.id)
                )
                await conn.execute(
                    configuracoes_usuario.insert().values(
                        usuario_id=uid,
                        modo=Modo.ESSENCIAL.value,
                        layout={},
                        atualizado_em=_dt(novo.criado_em),
                    )
                )
        except IntegrityError:
            raise ErroEmailDuplicado(novo.email) from None
        u = await self.usuario_por_id(int(uid))
        if u is None:  # pragma: no cover - acabou de ser inserido na mesma conexão
            raise RuntimeError("usuário recém-criado não encontrado")
        return u

    async def _um_usuario(self, condicao: Any) -> Usuario | None:
        async with self._engine.connect() as conn:
            linha = (await conn.execute(_SELECAO_USUARIO.where(condicao))).first()
        return None if linha is None else _usuario(linha)

    async def usuario_por_id(self, usuario_id: int) -> Usuario | None:
        return await self._um_usuario(usuarios.c.id == usuario_id)

    async def usuario_por_email(self, email: str) -> Usuario | None:
        return await self._um_usuario(usuarios.c.email == email)

    async def listar_usuarios(
        self, busca: str | None, status: StatusUsuario | None
    ) -> list[Usuario]:
        stmt = _SELECAO_USUARIO.order_by(usuarios.c.id)
        if status is not None:
            stmt = stmt.where(usuarios.c.status == status.value)
        if busca:
            termo = f"%{_escapar_like(busca)}%"
            stmt = stmt.where(
                or_(
                    usuarios.c.email.ilike(termo, escape="\\"),
                    usuarios.c.nome.ilike(termo, escape="\\"),
                )
            )
        async with self._engine.connect() as conn:
            return [_usuario(linha) for linha in (await conn.execute(stmt)).all()]

    async def salvar_usuario(self, usuario: Usuario) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                update(usuarios)
                .where(usuarios.c.id == usuario.id)
                .values(
                    email=usuario.email,
                    nome=usuario.nome,
                    papel=usuario.papel.value,
                    status=usuario.status.value,
                    senha_hash=usuario.senha_hash,
                    totp_cifrado=usuario.totp_cifrado,
                    totp_ultimo_passo=usuario.totp_ultimo_passo,
                )
            )
            stmt = insert(configuracoes_usuario).values(
                usuario_id=usuario.id,
                modo=usuario.modo.value,
                layout=usuario.layout,
                atualizado_em=func.now(),
            )
            await conn.execute(
                stmt.on_conflict_do_update(
                    index_elements=["usuario_id"],
                    set_={
                        "modo": stmt.excluded.modo,
                        "layout": stmt.excluded.layout,
                        "atualizado_em": func.now(),
                    },
                )
            )

    # --------------------------------------------------------------- sessões
    async def criar_sessao(self, sessao: Sessao) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(sessoes.insert().values(**_sessao_valores(sessao)))

    async def sessao(self, token_hash: str) -> Sessao | None:
        async with self._engine.connect() as conn:
            linha = (
                await conn.execute(select(sessoes).where(sessoes.c.token_hash == token_hash))
            ).first()
        return None if linha is None else _sessao(linha)

    async def salvar_sessao(self, sessao: Sessao) -> None:
        valores = _sessao_valores(sessao)
        del valores["token_hash"]
        async with self._engine.begin() as conn:
            await conn.execute(
                update(sessoes).where(sessoes.c.token_hash == sessao.token_hash).values(**valores)
            )

    async def sessoes_ativas(self, usuario_id: int, agora: InstanteMs) -> list[Sessao]:
        stmt = (
            select(sessoes)
            .where(
                sessoes.c.usuario_id == usuario_id,
                sessoes.c.revogada_em.is_(None),
                sessoes.c.expira_em > _dt(agora),
            )
            .order_by(sessoes.c.criada_em, sessoes.c.token_hash)
        )
        async with self._engine.connect() as conn:
            return [_sessao(linha) for linha in (await conn.execute(stmt)).all()]

    async def revogar_sessoes(
        self, usuario_id: int, agora: InstanteMs, motivo: str, exceto: str | None = None
    ) -> int:
        condicao = and_(sessoes.c.usuario_id == usuario_id, sessoes.c.revogada_em.is_(None))
        if exceto is not None:
            condicao = and_(condicao, sessoes.c.token_hash != exceto)
        async with self._engine.begin() as conn:
            resultado = await conn.execute(
                update(sessoes)
                .where(condicao)
                .values(revogada_em=_dt(agora), motivo_revogacao=motivo)
                .returning(sessoes.c.token_hash)
            )
            return len(resultado.all())

    # ---------------------------------------------------- planos e assinaturas
    async def criar_plano(self, novo: NovoPlano) -> Plano:
        async with self._engine.begin() as conn:
            linha = (
                await conn.execute(
                    planos.insert()
                    .values(
                        nome=novo.nome,
                        duracao_dias=novo.duracao_dias,
                        preco_centavos=novo.preco_centavos,
                        recursos=_recursos_json(novo.recursos),
                        ativo=novo.ativo,
                    )
                    .returning(*planos.c)
                )
            ).one()
        return _plano(linha)

    async def _um_plano(self, condicao: Any) -> Plano | None:
        async with self._engine.connect() as conn:
            linha = (await conn.execute(select(planos).where(condicao))).first()
        return None if linha is None else _plano(linha)

    async def plano(self, plano_id: int) -> Plano | None:
        return await self._um_plano(planos.c.id == plano_id)

    async def plano_por_nome(self, nome: str) -> Plano | None:
        return await self._um_plano(planos.c.nome == nome)

    async def listar_planos(self) -> list[Plano]:
        async with self._engine.connect() as conn:
            linhas = (await conn.execute(select(planos).order_by(planos.c.id))).all()
        return [_plano(linha) for linha in linhas]

    async def salvar_plano(self, plano: Plano) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                update(planos)
                .where(planos.c.id == plano.id)
                .values(
                    nome=plano.nome,
                    duracao_dias=plano.duracao_dias,
                    preco_centavos=plano.preco_centavos,
                    recursos=_recursos_json(plano.recursos),
                    ativo=plano.ativo,
                )
            )

    async def criar_assinatura(
        self,
        usuario_id: int,
        plano_id: int,
        inicio: InstanteMs,
        fim: InstanteMs,
        origem: str,
        agora: InstanteMs,
    ) -> Assinatura:
        async with self._engine.begin() as conn:
            linha = (
                await conn.execute(
                    assinaturas.insert()
                    .values(
                        usuario_id=usuario_id,
                        plano_id=plano_id,
                        inicio=_dt(inicio),
                        fim=_dt(fim),
                        origem=origem,
                        criado_em=_dt(agora),
                    )
                    .returning(*assinaturas.c)
                )
            ).one()
        return _assinatura(linha)

    async def assinatura_atual(self, usuario_id: int, agora: InstanteMs) -> Assinatura | None:
        stmt = (
            select(assinaturas)
            .where(assinaturas.c.usuario_id == usuario_id, assinaturas.c.inicio <= _dt(agora))
            .order_by(assinaturas.c.fim.desc(), assinaturas.c.id.desc())
            .limit(1)
        )
        async with self._engine.connect() as conn:
            linha = (await conn.execute(stmt)).first()
        return None if linha is None else _assinatura(linha)

    # ------------------------------------------------------------------ logs
    async def registrar_acesso(
        self, usuario_id: int | None, evento: str, ip: str, user_agent: str, t: InstanteMs
    ) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                registros_acesso.insert().values(
                    usuario_id=usuario_id,
                    evento=evento[:32],
                    ip=ip[:64],
                    user_agent=user_agent[:256],
                    t=_dt(t),
                )
            )

    async def listar_acessos(self, usuario_id: int | None, limite: int) -> list[RegistroAcesso]:
        t = registros_acesso
        stmt = select(t).order_by(t.c.t.desc(), t.c.id.desc()).limit(limite)
        if usuario_id is not None:
            stmt = stmt.where(t.c.usuario_id == usuario_id)
        async with self._engine.connect() as conn:
            linhas = (await conn.execute(stmt)).all()
        return [
            RegistroAcesso(
                int(r.id),
                None if r.usuario_id is None else int(r.usuario_id),
                r.evento,
                r.ip,
                r.user_agent,
                de_datetime(r.t),
            )
            for r in linhas
        ]

    async def registrar_auditoria(
        self,
        admin_id: int,
        acao: str,
        alvo: str,
        antes: dict[str, Any] | None,
        depois: dict[str, Any] | None,
        t: InstanteMs,
    ) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                auditoria.insert().values(
                    admin_id=admin_id, acao=acao, alvo=alvo, antes=antes, depois=depois, t=_dt(t)
                )
            )

    async def listar_auditoria(self, limite: int) -> list[RegistroAuditoria]:
        a = auditoria
        stmt = select(a).order_by(a.c.t.desc(), a.c.id.desc()).limit(limite)
        async with self._engine.connect() as conn:
            linhas = (await conn.execute(stmt)).all()
        return [
            RegistroAuditoria(
                int(r.id), int(r.admin_id), r.acao, r.alvo, r.antes, r.depois, de_datetime(r.t)
            )
            for r in linhas
        ]

    # ------------------------------------------------------------- corretoras
    async def payouts_vigentes(self, corretora: str, agora: InstanteMs) -> list[ItemPayout]:
        p, ca, c = corretora_payouts, corretora_ativos, corretoras
        instante = _dt(agora)
        stmt = (
            select(ca.c.simbolo, p.c.expiracao_s, p.c.payout)
            .select_from(
                p.join(ca, ca.c.id == p.c.corretora_ativo_id).join(c, c.c.id == ca.c.corretora_id)
            )
            .where(
                c.c.nome == corretora,
                p.c.valido_de <= instante,
                or_(p.c.valido_ate.is_(None), p.c.valido_ate > instante),
            )
            .order_by(ca.c.simbolo, p.c.expiracao_s)
        )
        async with self._engine.connect() as conn:
            linhas = (await conn.execute(stmt)).all()
        return [ItemPayout(s, ROTULO_EXPIRACAO[int(e)], float(v)) for s, e, v in linhas]

    async def substituir_payouts(
        self, corretora: str, itens: Sequence[ItemPayout], agora: InstanteMs
    ) -> None:
        ca, c = corretora_ativos, corretoras
        instante = _dt(agora)
        async with self._engine.begin() as conn:
            ids = {
                s: int(i)
                for s, i in (
                    await conn.execute(
                        select(ca.c.simbolo, ca.c.id)
                        .select_from(ca.join(c, c.c.id == ca.c.corretora_id))
                        .where(c.c.nome == corretora)
                    )
                ).all()
            }
            await conn.execute(
                update(corretora_payouts)
                .where(
                    corretora_payouts.c.corretora_ativo_id.in_(list(ids.values()) or [-1]),
                    corretora_payouts.c.valido_ate.is_(None),
                )
                .values(valido_ate=instante)
            )
            if itens:
                faltando = {i.simbolo for i in itens} - set(ids)
                if faltando:
                    raise ValueError(f"ativos sem cadastro na corretora: {sorted(faltando)}")
                await conn.execute(
                    corretora_payouts.insert(),
                    [
                        {
                            "corretora_ativo_id": ids[i.simbolo],
                            "expiracao_s": EXPIRACAO_S[i.expiracao],
                            "payout": i.payout,
                            "valido_de": instante,
                        }
                        for i in itens
                    ],
                )
