"""Porta de persistência das contas (usuários, sessões, planos, assinaturas, logs, payouts)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol

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
from sinais.core.tempo import InstanteMs


class ErroEmailDuplicado(Exception):
    """Já existe usuário com este e-mail."""


# Colunas que ``atualizar_usuario`` pode mudar. Escritas parciais: uma requisição com uma
# fotografia antiga do usuário nunca desfaz um bloqueio ou uma troca de senha concorrente.
CAMPOS_USUARIO = frozenset(
    {"email", "nome", "papel", "status", "senha_hash", "totp_cifrado", "totp_ultimo_passo"}
)


class RepositorioContas(Protocol):
    # Usuários. E-mails chegam normalizados (minúsculas, sem espaços) do serviço.
    async def criar_usuario(self, novo: NovoUsuario) -> Usuario: ...

    async def usuario_por_id(self, usuario_id: int) -> Usuario | None: ...

    async def usuario_por_email(self, email: str) -> Usuario | None: ...

    async def listar_usuarios(
        self, busca: str | None, status: StatusUsuario | None
    ) -> list[Usuario]:
        """Em ordem de id. ``busca`` procura no e-mail e no nome, sem diferenciar caixa."""
        ...

    async def salvar_usuario(self, usuario: Usuario) -> None:
        """Grava a linha inteira. Só para carga inicial e testes; os fluxos usam as escritas
        parciais abaixo."""
        ...

    async def atualizar_usuario(self, usuario_id: int, campos: Mapping[str, Any]) -> None:
        """Muda só ``campos`` (chaves de ``CAMPOS_USUARIO``; outra chave → ``ValueError``).
        E-mail já usado → ``ErroEmailDuplicado``."""
        ...

    async def atualizar_preferencias(
        self, usuario_id: int, modo: Modo | None, layout: dict[str, Any] | None
    ) -> Usuario | None:
        """Muda só o que vier preenchido e devolve o usuário atualizado."""
        ...

    async def registrar_passo_totp(self, usuario_id: int, passo: int) -> bool:
        """Grava ``passo`` só se for maior que o último usado (condicional e atômico): dois
        logins com o mesmo código não passam os dois."""
        ...

    # Sessões
    async def criar_sessao(self, sessao: Sessao) -> None: ...

    async def sessao(self, token_hash: str) -> Sessao | None: ...

    async def salvar_sessao(self, sessao: Sessao) -> None: ...

    async def tocar_sessao(self, token_hash: str, agora: InstanteMs) -> bool:
        """Atualiza ``ultimo_uso`` só se a sessão não estiver revogada. Devolve se atualizou."""
        ...

    async def revogar_sessao(self, token_hash: str, agora: InstanteMs, motivo: str) -> bool:
        """Revoga se ainda não estiver revogada. Devolve se revogou."""
        ...

    async def revogar_excedentes(
        self, usuario_id: int, manter: int, agora: InstanteMs, motivo: str
    ) -> int:
        """Revoga as sessões ativas além das ``manter`` mais novas (por criação e hash, ordem
        determinística: dois logins simultâneos chegam ao mesmo resultado)."""
        ...

    async def sessoes_ativas(self, usuario_id: int, agora: InstanteMs) -> list[Sessao]:
        """Não revogadas e não expiradas, da mais antiga para a mais nova."""
        ...

    async def revogar_sessoes(
        self, usuario_id: int, agora: InstanteMs, motivo: str, exceto: str | None = None
    ) -> int:
        """Revoga as sessões ainda não revogadas do usuário. Devolve quantas."""
        ...

    # Planos e assinaturas
    async def criar_plano(self, novo: NovoPlano) -> Plano: ...

    async def plano(self, plano_id: int) -> Plano | None: ...

    async def plano_por_nome(self, nome: str) -> Plano | None: ...

    async def listar_planos(self) -> list[Plano]: ...

    async def salvar_plano(self, plano: Plano) -> None: ...

    async def criar_assinatura(
        self,
        usuario_id: int,
        plano_id: int,
        inicio: InstanteMs,
        fim: InstanteMs,
        origem: str,
        agora: InstanteMs,
    ) -> Assinatura: ...

    async def assinatura(self, assinatura_id: int) -> Assinatura | None: ...

    async def encerrar_assinatura(self, assinatura_id: int, agora: InstanteMs) -> Assinatura | None:
        """Antecipa o fim para ``agora`` (nunca estica uma já encerrada)."""
        ...

    async def assinatura_atual(self, usuario_id: int, agora: InstanteMs) -> Assinatura | None:
        """A de maior ``fim`` entre as já iniciadas (``inicio <= agora``), mesmo vencida."""
        ...

    # Logs
    async def registrar_acesso(
        self, usuario_id: int | None, evento: str, ip: str, user_agent: str, t: InstanteMs
    ) -> None: ...

    async def listar_acessos(self, usuario_id: int | None, limite: int) -> list[RegistroAcesso]:
        """Do mais novo para o mais antigo."""
        ...

    async def registrar_auditoria(
        self,
        admin_id: int,
        acao: str,
        alvo: str,
        antes: dict[str, Any] | None,
        depois: dict[str, Any] | None,
        t: InstanteMs,
    ) -> None: ...

    async def listar_auditoria(self, limite: int) -> list[RegistroAuditoria]: ...

    # Corretoras
    async def payouts_vigentes(self, corretora: str, agora: InstanteMs) -> list[ItemPayout]:
        """Payouts válidos em ``agora``, ordenados por símbolo e expiração."""
        ...

    async def substituir_payouts(
        self, corretora: str, itens: Sequence[ItemPayout], agora: InstanteMs
    ) -> None:
        """Encerra os vigentes em ``agora`` e grava ``itens`` a partir de ``agora``."""
        ...
