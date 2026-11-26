"""Repositório de contas em memória: dublê de testes com o mesmo contrato do PostgreSQL."""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

from sinais.contas.modelos import (
    Assinatura,
    ItemPayout,
    Modo,
    NovoPlano,
    NovoUsuario,
    Plano,
    RegistroAcesso,
    RegistroAuditoria,
    Sessao,
    StatusUsuario,
    Usuario,
)
from sinais.contas.repositorio import CAMPOS_USUARIO, ErroEmailDuplicado
from sinais.core.dominio import EXPIRACAO_POR_ROTULO
from sinais.core.tempo import InstanteMs

_ORDEM_EXPIRACAO = {r: int(e) for r, e in EXPIRACAO_POR_ROTULO.items()}


@dataclass(frozen=True, slots=True)
class _Payout:
    corretora: str
    item: ItemPayout
    valido_de: InstanteMs
    valido_ate: InstanteMs | None


def chave_payout(item: ItemPayout) -> tuple[str, int, str]:
    return (item.simbolo, _ORDEM_EXPIRACAO.get(item.expiracao, 10**6), item.expiracao)


class RepositorioContasMemoria:
    def __init__(self) -> None:
        self._usuarios: dict[int, Usuario] = {}
        self._sessoes: dict[str, Sessao] = {}
        self._ordem_sessao: dict[str, int] = {}
        self._planos: dict[int, Plano] = {}
        self._assinaturas: list[Assinatura] = []
        self._acessos: list[RegistroAcesso] = []
        self._auditoria: list[RegistroAuditoria] = []
        self._payouts: list[_Payout] = []
        self._seq = 0

    def _id(self) -> int:
        self._seq += 1
        return self._seq

    async def criar_usuario(self, novo: NovoUsuario) -> Usuario:
        if any(u.email == novo.email for u in self._usuarios.values()):
            raise ErroEmailDuplicado(novo.email)
        u = Usuario(
            id=self._id(),
            email=novo.email,
            nome=novo.nome,
            papel=novo.papel,
            status=StatusUsuario.ATIVO,
            senha_hash=novo.senha_hash,
            totp_cifrado=novo.totp_cifrado,
            totp_ultimo_passo=None,
            modo=Modo.ESSENCIAL,
            layout={},
            criado_em=novo.criado_em,
        )
        self._usuarios[u.id] = u
        return u

    async def usuario_por_id(self, usuario_id: int) -> Usuario | None:
        return self._usuarios.get(usuario_id)

    async def usuario_por_email(self, email: str) -> Usuario | None:
        return next((u for u in self._usuarios.values() if u.email == email), None)

    async def listar_usuarios(
        self, busca: str | None, status: StatusUsuario | None
    ) -> list[Usuario]:
        termo = busca.lower() if busca else None
        return [
            u
            for _, u in sorted(self._usuarios.items())
            if (status is None or u.status is status)
            and (termo is None or termo in u.email.lower() or termo in u.nome.lower())
        ]

    async def salvar_usuario(self, usuario: Usuario) -> None:
        self._usuarios[usuario.id] = replace(usuario, layout=copy.deepcopy(usuario.layout))

    async def atualizar_usuario(self, usuario_id: int, campos: Mapping[str, Any]) -> None:
        if not set(campos) <= CAMPOS_USUARIO:
            raise ValueError(f"campos não permitidos: {sorted(set(campos) - CAMPOS_USUARIO)}")
        u = self._usuarios.get(usuario_id)
        if u is None:
            return
        email = campos.get("email")
        if email is not None and any(
            o.email == email and o.id != usuario_id for o in self._usuarios.values()
        ):
            raise ErroEmailDuplicado(str(email))
        self._usuarios[usuario_id] = replace(u, **dict(campos))

    async def atualizar_preferencias(
        self, usuario_id: int, modo: Modo | None, layout: dict[str, Any] | None
    ) -> Usuario | None:
        u = self._usuarios.get(usuario_id)
        if u is None:
            return None
        if modo is not None:
            u = replace(u, modo=modo)
        if layout is not None:
            u = replace(u, layout=copy.deepcopy(layout))
        self._usuarios[usuario_id] = u
        return u

    async def registrar_passo_totp(self, usuario_id: int, passo: int) -> bool:
        u = self._usuarios.get(usuario_id)
        if u is None or (u.totp_ultimo_passo is not None and passo <= u.totp_ultimo_passo):
            return False
        self._usuarios[usuario_id] = replace(u, totp_ultimo_passo=passo)
        return True

    async def criar_sessao(self, sessao: Sessao) -> None:
        self._sessoes[sessao.token_hash] = sessao
        self._ordem_sessao[sessao.token_hash] = self._id()

    async def sessao(self, token_hash: str) -> Sessao | None:
        return self._sessoes.get(token_hash)

    async def salvar_sessao(self, sessao: Sessao) -> None:
        self._sessoes[sessao.token_hash] = sessao

    async def tocar_sessao(self, token_hash: str, agora: InstanteMs) -> bool:
        s = self._sessoes.get(token_hash)
        if s is None or s.revogada_em is not None:
            return False
        self._sessoes[token_hash] = replace(s, ultimo_uso=agora)
        return True

    async def revogar_sessao(self, token_hash: str, agora: InstanteMs, motivo: str) -> bool:
        s = self._sessoes.get(token_hash)
        if s is None or s.revogada_em is not None:
            return False
        self._sessoes[token_hash] = replace(s, revogada_em=agora, motivo_revogacao=motivo)
        return True

    async def revogar_excedentes(
        self, usuario_id: int, manter: int, agora: InstanteMs, motivo: str
    ) -> int:
        ativas = [
            s
            for s in self._sessoes.values()
            if s.usuario_id == usuario_id and s.revogada_em is None
        ]
        ativas.sort(key=lambda s: (s.criada_em, self._ordem_sessao[s.token_hash]), reverse=True)
        for s in ativas[manter:]:
            self._sessoes[s.token_hash] = replace(s, revogada_em=agora, motivo_revogacao=motivo)
        return len(ativas[manter:])

    async def sessoes_ativas(self, usuario_id: int, agora: InstanteMs) -> list[Sessao]:
        ativas = [
            s
            for s in self._sessoes.values()
            if s.usuario_id == usuario_id and s.revogada_em is None and s.expira_em > agora
        ]
        return sorted(ativas, key=lambda s: (s.criada_em, s.token_hash))

    async def revogar_sessoes(
        self, usuario_id: int, agora: InstanteMs, motivo: str, exceto: str | None = None
    ) -> int:
        n = 0
        for h, s in list(self._sessoes.items()):
            if s.usuario_id == usuario_id and s.revogada_em is None and h != exceto:
                self._sessoes[h] = replace(s, revogada_em=agora, motivo_revogacao=motivo)
                n += 1
        return n

    async def criar_plano(self, novo: NovoPlano) -> Plano:
        p = Plano(
            self._id(),
            novo.nome,
            novo.duracao_dias,
            novo.preco_centavos,
            novo.recursos,
            novo.ativo,
        )
        self._planos[p.id] = p
        return p

    async def plano(self, plano_id: int) -> Plano | None:
        return self._planos.get(plano_id)

    async def plano_por_nome(self, nome: str) -> Plano | None:
        return next((p for p in self._planos.values() if p.nome == nome), None)

    async def listar_planos(self) -> list[Plano]:
        return [p for _, p in sorted(self._planos.items())]

    async def salvar_plano(self, plano: Plano) -> None:
        self._planos[plano.id] = plano

    async def criar_assinatura(
        self,
        usuario_id: int,
        plano_id: int,
        inicio: InstanteMs,
        fim: InstanteMs,
        origem: str,
        agora: InstanteMs,
    ) -> Assinatura:
        a = Assinatura(self._id(), usuario_id, plano_id, inicio, fim, origem, agora)
        self._assinaturas.append(a)
        return a

    async def assinatura(self, assinatura_id: int) -> Assinatura | None:
        return next((a for a in self._assinaturas if a.id == assinatura_id), None)

    async def encerrar_assinatura(self, assinatura_id: int, agora: InstanteMs) -> Assinatura | None:
        for i, a in enumerate(self._assinaturas):
            if a.id == assinatura_id:
                if a.fim > agora:
                    self._assinaturas[i] = a = replace(a, fim=max(agora, a.inicio + 1))
                return a
        return None

    async def assinatura_atual(self, usuario_id: int, agora: InstanteMs) -> Assinatura | None:
        candidatas = [
            a for a in self._assinaturas if a.usuario_id == usuario_id and a.inicio <= agora
        ]
        return max(candidatas, key=lambda a: (a.fim, a.id), default=None)

    async def registrar_acesso(
        self, usuario_id: int | None, evento: str, ip: str, user_agent: str, t: InstanteMs
    ) -> None:
        self._acessos.append(RegistroAcesso(self._id(), usuario_id, evento, ip, user_agent, t))

    async def listar_acessos(self, usuario_id: int | None, limite: int) -> list[RegistroAcesso]:
        filtrados = [a for a in self._acessos if usuario_id is None or a.usuario_id == usuario_id]
        return sorted(filtrados, key=lambda a: (a.t, a.id), reverse=True)[:limite]

    async def registrar_auditoria(
        self,
        admin_id: int,
        acao: str,
        alvo: str,
        antes: dict[str, Any] | None,
        depois: dict[str, Any] | None,
        t: InstanteMs,
    ) -> None:
        self._auditoria.append(
            RegistroAuditoria(
                self._id(), admin_id, acao, alvo, copy.deepcopy(antes), copy.deepcopy(depois), t
            )
        )

    async def listar_auditoria(self, limite: int) -> list[RegistroAuditoria]:
        return sorted(self._auditoria, key=lambda r: (r.t, r.id), reverse=True)[:limite]

    async def payouts_vigentes(self, corretora: str, agora: InstanteMs) -> list[ItemPayout]:
        vigentes = [
            p.item
            for p in self._payouts
            if p.corretora == corretora
            and p.valido_de <= agora
            and (p.valido_ate is None or agora < p.valido_ate)
        ]
        return sorted(vigentes, key=chave_payout)

    async def substituir_payouts(
        self, corretora: str, itens: Sequence[ItemPayout], agora: InstanteMs
    ) -> None:
        self._payouts = [
            replace(p, valido_ate=agora) if p.corretora == corretora and p.valido_ate is None else p
            for p in self._payouts
        ]
        self._payouts.extend(_Payout(corretora, i, agora, None) for i in itens)
