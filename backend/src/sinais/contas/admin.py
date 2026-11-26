"""Operações do administrador (Fase 10). Toda mudança grava ``auditoria`` com antes e depois.

As fotografias da auditoria nunca incluem hash de senha, senha temporária nem segredo TOTP.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import asdict, dataclass, replace
from typing import Any

from sinais.contas.contexto import Contexto
from sinais.contas.modelos import (
    Assinatura,
    ItemPayout,
    NovoPlano,
    NovoUsuario,
    Papel,
    Plano,
    Recursos,
    RegistroAcesso,
    RegistroAuditoria,
    StatusUsuario,
    Usuario,
)
from sinais.contas.repositorio import ErroEmailDuplicado
from sinais.contas.servico import ErroConta, ServicoContas, normalizar_email, validar_senha_nova
from sinais.core.dominio import ROTULOS_EXPIRACAO
from sinais.core.tempo import InstanteMs

EXPIRACOES = tuple(ROTULOS_EXPIRACAO.values())
CORRETORA_EXNOVA = "exnova"
_DIA_MS = 86_400_000
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PAYOUT_MAXIMO = 1.0


@dataclass(frozen=True, slots=True)
class FichaUsuario:
    usuario: Usuario
    assinatura: Assinatura | None
    plano: Plano | None


def foto_usuario(u: Usuario) -> dict[str, Any]:
    return {
        "id": u.id,
        "email": u.email,
        "nome": u.nome,
        "papel": u.papel.value,
        "status": u.status.value,
        "modo": u.modo.value,
    }


def foto_plano(p: Plano) -> dict[str, Any]:
    d = asdict(p)
    d["recursos"] = {k: list(v) if isinstance(v, tuple) else v for k, v in d["recursos"].items()}
    return d


class ServicoAdmin:
    def __init__(self, contas: ServicoContas, ativos: Sequence[str]) -> None:
        self._c = contas
        self._repo = contas.repo
        self._ativos = tuple(ativos)

    async def _auditar(
        self,
        ctx: Contexto,
        acao: str,
        alvo: str,
        antes: dict[str, Any] | None,
        depois: dict[str, Any] | None,
    ) -> None:
        await self._repo.registrar_auditoria(
            ctx.usuario.id, acao, alvo, antes, depois, self._c.relogio.agora_ms()
        )

    async def _ficha(self, u: Usuario) -> FichaUsuario:
        a = await self._repo.assinatura_atual(u.id, self._c.relogio.agora_ms())
        p = await self._repo.plano(a.plano_id) if a else None
        return FichaUsuario(u, a, p)

    async def _plano_ref(self, ref: int | str) -> Plano:
        p = await (
            self._repo.plano(ref) if isinstance(ref, int) else self._repo.plano_por_nome(ref)
        )
        if p is None:
            raise ErroConta(422, "plano_inexistente", "Plano não encontrado.")
        return p

    # ------------------------------------------------------------- usuários
    async def listar_usuarios(
        self, busca: str | None, status: StatusUsuario | None
    ) -> list[FichaUsuario]:
        return [await self._ficha(u) for u in await self._repo.listar_usuarios(busca, status)]

    async def criar_usuario(
        self,
        ctx: Contexto,
        email: str,
        nome: str,
        senha_temporaria: str,
        plano: int | str,
        vence_em: InstanteMs | None,
    ) -> FichaUsuario:
        agora = self._c.relogio.agora_ms()
        email = normalizar_email(email)
        if not _EMAIL.match(email) or len(email) > 254:
            raise ErroConta(422, "email_invalido", "E-mail inválido.")
        validar_senha_nova(senha_temporaria)
        p = await self._plano_ref(plano)
        fim = vence_em if vence_em is not None else agora + p.duracao_dias * _DIA_MS
        if fim <= agora:
            raise ErroConta(422, "vencimento_invalido", "O vencimento deve estar no futuro.")
        try:
            u = await self._repo.criar_usuario(
                NovoUsuario(
                    email,
                    nome.strip(),
                    Papel.CLIENTE,
                    await self._c.gerar_hash(senha_temporaria),
                    agora,
                )
            )
        except ErroEmailDuplicado:
            raise ErroConta(409, "email_em_uso", "Já existe uma conta com este e-mail.") from None
        a = await self._repo.criar_assinatura(u.id, p.id, agora, fim, "manual", agora)
        await self._auditar(
            ctx,
            "usuario.criar",
            f"usuario:{u.id}",
            None,
            {**foto_usuario(u), "plano_id": p.id, "vence_em": fim},
        )
        return FichaUsuario(u, a, p)

    async def editar_usuario(
        self,
        ctx: Contexto,
        usuario_id: int,
        *,
        nome: str | None = None,
        email: str | None = None,
        status: StatusUsuario | None = None,
        senha_temporaria: str | None = None,
    ) -> FichaUsuario:
        agora = self._c.relogio.agora_ms()
        u = await self._repo.usuario_por_id(usuario_id)
        if u is None:
            raise ErroConta(404, "usuario_inexistente", "Usuário não encontrado.")
        if status is not None and u.id == ctx.usuario.id and status is not StatusUsuario.ATIVO:
            raise ErroConta(422, "acao_invalida", "Você não pode bloquear a própria conta.")
        novo = u
        campos: dict[str, Any] = {}
        if nome is not None:
            novo = replace(novo, nome=nome.strip())
            campos["nome"] = novo.nome
        if email is not None:
            e = normalizar_email(email)
            if not _EMAIL.match(e):
                raise ErroConta(422, "email_invalido", "E-mail inválido.")
            outro = await self._repo.usuario_por_email(e)
            if outro is not None and outro.id != u.id:
                raise ErroConta(409, "email_em_uso", "Já existe uma conta com este e-mail.")
            novo = replace(novo, email=e)
            campos["email"] = e
        if status is not None:
            novo = replace(novo, status=status)
            campos["status"] = status
        if senha_temporaria is not None:
            validar_senha_nova(senha_temporaria)
            campos["senha_hash"] = await self._c.gerar_hash(senha_temporaria)
        try:
            # Só as colunas pedidas: nunca desfaz outra mudança feita ao mesmo tempo.
            await self._repo.atualizar_usuario(u.id, campos)
        except ErroEmailDuplicado:
            raise ErroConta(409, "email_em_uso", "Já existe uma conta com este e-mail.") from None
        if (status is not None and status is not StatusUsuario.ATIVO) or senha_temporaria:
            motivo = "senha_redefinida" if senha_temporaria else f"usuario_{status}"
            await self._repo.revogar_sessoes(u.id, agora, motivo)
        depois = foto_usuario(novo)
        if senha_temporaria is not None:
            depois["senha_redefinida"] = True
        await self._auditar(ctx, "usuario.editar", f"usuario:{u.id}", foto_usuario(u), depois)
        return await self._ficha(novo)

    # --------------------------------------------------------------- planos
    def _validar_plano(self, duracao_dias: int, preco_centavos: int, recursos: Recursos) -> None:
        if duracao_dias <= 0 or duracao_dias > 3660 or preco_centavos < 0:
            raise ErroConta(422, "plano_invalido", "Duração ou preço do plano inválidos.")
        if not set(recursos.ativos) <= set(self._ativos):
            raise ErroConta(422, "plano_invalido", "O plano cita um ativo desconhecido.")
        if not set(recursos.expiracoes) <= set(EXPIRACOES):
            raise ErroConta(422, "plano_invalido", "O plano cita uma expiração desconhecida.")

    async def listar_planos(self) -> list[Plano]:
        return await self._repo.listar_planos()

    async def criar_plano(
        self,
        ctx: Contexto,
        nome: str,
        duracao_dias: int,
        preco_centavos: int,
        recursos: Recursos,
        ativo: bool,
    ) -> Plano:
        nome = nome.strip()
        self._validar_plano(duracao_dias, preco_centavos, recursos)
        if not nome or await self._repo.plano_por_nome(nome) is not None:
            raise ErroConta(409, "plano_existente", "Já existe um plano com este nome.")
        p = await self._repo.criar_plano(
            NovoPlano(nome, duracao_dias, preco_centavos, recursos, ativo)
        )
        await self._auditar(ctx, "plano.criar", f"plano:{p.id}", None, foto_plano(p))
        return p

    async def editar_plano(
        self,
        ctx: Contexto,
        plano_id: int,
        *,
        nome: str | None = None,
        duracao_dias: int | None = None,
        preco_centavos: int | None = None,
        recursos: Recursos | None = None,
        ativo: bool | None = None,
    ) -> Plano:
        p = await self._repo.plano(plano_id)
        if p is None:
            raise ErroConta(404, "plano_inexistente", "Plano não encontrado.")
        novo = replace(
            p,
            nome=nome.strip() if nome is not None else p.nome,
            duracao_dias=duracao_dias if duracao_dias is not None else p.duracao_dias,
            preco_centavos=preco_centavos if preco_centavos is not None else p.preco_centavos,
            recursos=recursos if recursos is not None else p.recursos,
            ativo=ativo if ativo is not None else p.ativo,
        )
        self._validar_plano(novo.duracao_dias, novo.preco_centavos, novo.recursos)
        mesmo_nome = await self._repo.plano_por_nome(novo.nome)
        if not novo.nome or (mesmo_nome is not None and mesmo_nome.id != p.id):
            raise ErroConta(409, "plano_existente", "Já existe um plano com este nome.")
        await self._repo.salvar_plano(novo)
        await self._auditar(ctx, "plano.editar", f"plano:{p.id}", foto_plano(p), foto_plano(novo))
        return novo

    # ---------------------------------------------------------- assinaturas
    async def criar_assinatura(
        self, ctx: Contexto, usuario_id: int, plano_id: int, inicio: InstanteMs, fim: InstanteMs
    ) -> Assinatura:
        if await self._repo.usuario_por_id(usuario_id) is None:
            raise ErroConta(404, "usuario_inexistente", "Usuário não encontrado.")
        p = await self._plano_ref(plano_id)
        if fim <= inicio or inicio < 0:
            raise ErroConta(422, "periodo_invalido", "O fim deve ser posterior ao início.")
        agora = self._c.relogio.agora_ms()
        a = await self._repo.criar_assinatura(usuario_id, p.id, inicio, fim, "manual", agora)
        await self._auditar(ctx, "assinatura.criar", f"usuario:{usuario_id}", None, asdict(a))
        return a

    async def encerrar_assinatura(self, ctx: Contexto, assinatura_id: int) -> Assinatura:
        """Antecipa o fim da assinatura para agora (cancelamento, estorno). Vale na hora em
        REST e WebSocket."""
        antes = await self._repo.assinatura(assinatura_id)
        if antes is None:
            raise ErroConta(404, "assinatura_inexistente", "Assinatura não encontrada.")
        depois = await self._repo.encerrar_assinatura(assinatura_id, self._c.relogio.agora_ms())
        if depois is None:  # pragma: no cover - apagada entre as duas leituras
            raise ErroConta(404, "assinatura_inexistente", "Assinatura não encontrada.")
        await self._auditar(
            ctx, "assinatura.encerrar", f"usuario:{antes.usuario_id}", asdict(antes), asdict(depois)
        )
        return depois

    # ---------------------------------------------------------------- logs
    async def acessos(self, usuario_id: int | None, limite: int = 500) -> list[RegistroAcesso]:
        return await self._repo.listar_acessos(usuario_id, limite)

    async def auditoria(self, limite: int = 500) -> list[RegistroAuditoria]:
        return await self._repo.listar_auditoria(limite)

    # -------------------------------------------------------------- payouts
    async def payouts(self) -> list[ItemPayout]:
        return await self._repo.payouts_vigentes(CORRETORA_EXNOVA, self._c.relogio.agora_ms())

    async def substituir_payouts(
        self, ctx: Contexto, itens: Sequence[ItemPayout]
    ) -> list[ItemPayout]:
        vistos: set[tuple[str, str]] = set()
        for i in itens:
            chave = (i.simbolo, i.expiracao)
            if (
                i.simbolo not in self._ativos
                or i.expiracao not in EXPIRACOES
                or not 0 < i.payout <= PAYOUT_MAXIMO
                or chave in vistos
            ):
                raise ErroConta(
                    422,
                    "payout_invalido",
                    f"Payout inválido para {i.simbolo} {i.expiracao}: use um ativo conhecido, "
                    "uma expiração da V1, valor entre 0 e 1 e sem repetir.",
                )
            vistos.add(chave)
        antes = await self.payouts()
        await self._repo.substituir_payouts(CORRETORA_EXNOVA, itens, self._c.relogio.agora_ms())
        depois = await self.payouts()
        await self._auditar(
            ctx,
            "payout.substituir",
            f"corretora:{CORRETORA_EXNOVA}",
            {"itens": [asdict(i) for i in antes]},
            {"itens": [asdict(i) for i in depois]},
        )
        return depois
