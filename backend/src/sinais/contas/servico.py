"""Serviço de contas: login, sessões, CSRF, bloqueio, 2FA e assinatura (ADR-12, design §15).

Nada aqui registra senha, hash, token ou código TOTP em log: os logs de acesso guardam só o
evento, o usuário (quando conhecido), o IP e o user agent.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Any, NoReturn

from sinais.contas.autorizacao import pode_modo_avancado
from sinais.contas.contexto import Contexto
from sinais.contas.limites import ContadorLimites, PoliticaLogin
from sinais.contas.modelos import Modo, Papel, Sessao, StatusUsuario, Usuario
from sinais.contas.repositorio import RepositorioContas
from sinais.contas.seguranca import CifraSegredos, ErroCifra, gerar_token, hash_token, iguais
from sinais.contas.senhas import Hasher
from sinais.contas.totp import VerificadorTotp
from sinais.core.tempo import Relogio
from sinais.logs import obter_logger

_log = obter_logger(__name__)
_MINUTO_MS = 60_000
_DIA_MS = 86_400_000
SENHA_MINIMA = 10
SENHA_MAXIMA = 256
LAYOUT_MAXIMO_BYTES = 64 * 1024
MSG_CREDENCIAIS = "E-mail ou senha incorretos."


class ErroConta(Exception):
    """Erro de regra de conta, já com status HTTP, código curto e mensagem para o usuário."""

    def __init__(self, status: int, codigo: str, mensagem: str) -> None:
        super().__init__(codigo)
        self.status = status
        self.codigo = codigo
        self.mensagem = mensagem


def normalizar_email(email: str) -> str:
    return email.strip().lower()


def validar_senha_nova(senha: str) -> None:
    if len(senha) < SENHA_MINIMA or len(senha) > SENHA_MAXIMA:
        raise ErroConta(
            422,
            "senha_fraca",
            f"A senha deve ter entre {SENHA_MINIMA} e {SENHA_MAXIMA} caracteres.",
        )


@dataclass(frozen=True, slots=True)
class ParametrosContas:
    sessao_duracao_ms: int = 7 * _DIA_MS
    sessao_ociosa_ms: int = _DIA_MS
    sessoes_simultaneas: int = 1
    politica: PoliticaLogin = PoliticaLogin()


@dataclass(frozen=True, slots=True)
class ResultadoLogin:
    usuario: Usuario
    token: str
    csrf: str


class ServicoContas:
    def __init__(
        self,
        repo: RepositorioContas,
        hasher: Hasher,
        totp: VerificadorTotp,
        cifra: CifraSegredos,
        contador: ContadorLimites,
        relogio: Relogio,
        params: ParametrosContas | None = None,
    ) -> None:
        self.repo = repo
        self.hasher = hasher
        self.totp = totp
        self.cifra = cifra
        self._contador = contador
        self.relogio = relogio
        self.params = params or ParametrosContas()
        # Hash de uma senha aleatória descartada: e-mail inexistente gasta o mesmo tempo.
        self._hash_ficticio = hasher.gerar(gerar_token())

    # ------------------------------------------------------------------ login
    async def login(
        self, email: str, senha: str, totp: str | None, ip: str, user_agent: str
    ) -> ResultadoLogin:
        agora = self.relogio.agora_ms()
        email = normalizar_email(email)
        chave = hashlib.sha256(email.encode()).hexdigest()
        pol = self.params.politica
        n_ip = await self._contador.incrementar(f"login:ip:{ip}", pol.janela_s)
        n_email = await self._contador.incrementar(f"login:email:{chave}", pol.janela_s)
        usuario = await self.repo.usuario_por_email(email)
        uid = usuario.id if usuario else None
        if n_ip > pol.tentativas_por_ip or n_email > pol.tentativas_por_email:
            await self.repo.registrar_acesso(uid, "login_limite", ip, user_agent, agora)
            raise ErroConta(
                429, "muitas_tentativas", "Muitas tentativas. Aguarde um minuto e tente de novo."
            )
        bloqueio = await self._contador.ler(f"login:bloqueio:{chave}")
        if bloqueio is not None and int(bloqueio) > agora:
            await self.repo.registrar_acesso(uid, "login_bloqueado", ip, user_agent, agora)
            minutos = max(1, -(-(int(bloqueio) - agora) // _MINUTO_MS))
            raise ErroConta(
                423,
                "conta_bloqueada",
                f"Acesso bloqueado por excesso de tentativas. Tente de novo em {minutos} min.",
            )
        if usuario is None:
            self.hasher.verificar(self._hash_ficticio, senha)
            await self._falha(chave, None, ip, user_agent, agora)
        elif not self.hasher.verificar(usuario.senha_hash, senha):
            await self._falha(chave, usuario.id, ip, user_agent, agora)
        if usuario.status is StatusUsuario.DESATIVADO:
            await self.repo.registrar_acesso(usuario.id, "login_desativado", ip, user_agent, agora)
            raise ErroConta(401, "credenciais_invalidas", MSG_CREDENCIAIS)
        if usuario.status is StatusUsuario.BLOQUEADO:
            await self.repo.registrar_acesso(usuario.id, "login_bloqueado", ip, user_agent, agora)
            raise ErroConta(423, "conta_bloqueada", "Conta bloqueada. Fale com o suporte.")
        if usuario.papel is Papel.ADMIN:
            usuario = await self._verificar_totp(usuario, totp, chave, ip, user_agent, agora)
        await self._contador.apagar(f"login:falhas:{chave}")
        await self._contador.apagar(f"login:bloqueio:{chave}")
        if self.hasher.precisa_rehash(usuario.senha_hash):
            usuario = replace(usuario, senha_hash=self.hasher.gerar(senha))
            await self.repo.salvar_usuario(usuario)
        return await self._abrir_sessao(usuario, ip, user_agent, agora)

    async def _falha(
        self, chave: str, uid: int | None, ip: str, user_agent: str, agora: int, evento: str = ""
    ) -> NoReturn:
        pol = self.params.politica
        falhas = await self._contador.incrementar(f"login:falhas:{chave}", pol.memoria_falhas_s)
        espera = pol.bloqueio_s(falhas)
        if espera:
            await self._contador.gravar(
                f"login:bloqueio:{chave}", str(agora + espera * 1000), espera
            )
        await self.repo.registrar_acesso(uid, evento or "login_falha", ip, user_agent, agora)
        _log.warning("contas.login_falha", extra={"campos": {"usuario_id": uid, "ip": ip}})
        raise ErroConta(401, "credenciais_invalidas", MSG_CREDENCIAIS)

    async def _verificar_totp(
        self, usuario: Usuario, codigo: str | None, chave: str, ip: str, ua: str, agora: int
    ) -> Usuario:
        if not codigo:
            raise ErroConta(401, "totp_necessario", "Informe o código do autenticador.")
        passo: int | None = None
        if usuario.totp_cifrado:
            try:
                segredo = self.cifra.decifrar(usuario.totp_cifrado)
            except ErroCifra:
                _log.error("contas.totp_indecifravel", extra={"campos": {"usuario_id": usuario.id}})
                segredo = None
            if segredo:
                passo = self.totp.passo_valido(segredo, codigo.strip(), agora)
        ultimo = usuario.totp_ultimo_passo
        if passo is None or (ultimo is not None and passo <= ultimo):
            try:
                await self._falha(chave, usuario.id, ip, ua, agora, "totp_falha")
            except ErroConta:
                raise ErroConta(401, "totp_invalido", "Código do autenticador inválido.") from None
        novo = replace(usuario, totp_ultimo_passo=passo)
        await self.repo.salvar_usuario(novo)
        return novo

    async def _abrir_sessao(
        self, usuario: Usuario, ip: str, user_agent: str, agora: int
    ) -> ResultadoLogin:
        ativas = await self.repo.sessoes_ativas(usuario.id, agora)
        excesso = len(ativas) - self.params.sessoes_simultaneas + 1
        for s in ativas[: max(0, excesso)]:
            await self.repo.salvar_sessao(
                replace(s, revogada_em=agora, motivo_revogacao="limite_sessoes")
            )
        token, csrf = gerar_token(), gerar_token()
        await self.repo.criar_sessao(
            Sessao(
                token_hash=hash_token(token),
                csrf_hash=hash_token(csrf),
                usuario_id=usuario.id,
                criada_em=agora,
                ultimo_uso=agora,
                expira_em=agora + self.params.sessao_duracao_ms,
                ip=ip[:64],
                user_agent=user_agent[:256],
            )
        )
        await self.repo.registrar_acesso(usuario.id, "login", ip, user_agent, agora)
        _log.info("contas.login", extra={"campos": {"usuario_id": usuario.id}})
        return ResultadoLogin(usuario, token, csrf)

    # --------------------------------------------------------------- sessão
    async def autenticar(self, token: str | None) -> Contexto:
        invalida = ErroConta(401, "sessao_invalida", "Sessão expirada. Entre de novo.")
        if not token:
            raise invalida
        agora = self.relogio.agora_ms()
        sessao = await self.repo.sessao(hash_token(token))
        if sessao is None or sessao.revogada_em is not None or sessao.expira_em <= agora:
            raise invalida
        if agora - sessao.ultimo_uso > self.params.sessao_ociosa_ms:
            await self.repo.salvar_sessao(
                replace(sessao, revogada_em=agora, motivo_revogacao="ociosa")
            )
            raise invalida
        usuario = await self.repo.usuario_por_id(sessao.usuario_id)
        if usuario is None or usuario.status is not StatusUsuario.ATIVO:
            await self.repo.revogar_sessoes(sessao.usuario_id, agora, "usuario_inativo")
            raise invalida
        if agora - sessao.ultimo_uso >= _MINUTO_MS:
            sessao = replace(sessao, ultimo_uso=agora)
            await self.repo.salvar_sessao(sessao)
        assinatura = await self.repo.assinatura_atual(usuario.id, agora)
        plano = await self.repo.plano(assinatura.plano_id) if assinatura else None
        return Contexto(usuario, sessao, assinatura, plano, agora)

    def exigir_assinatura(self, ctx: Contexto) -> None:
        if ctx.admin:
            return
        if ctx.status_assinatura != "ativa":
            raise ErroConta(
                402,
                "assinatura_vencida",
                "Sua assinatura venceu ou não existe. Renove para continuar.",
            )

    def exigir_admin(self, ctx: Contexto) -> None:
        if not ctx.admin:
            raise ErroConta(403, "sem_permissao", "Você não tem permissão para esta ação.")

    def verificar_csrf(self, ctx: Contexto, cabecalho: str | None, cookie: str | None) -> None:
        if (
            not cabecalho
            or not cookie
            or not iguais(cabecalho, cookie)
            or not iguais(hash_token(cabecalho), ctx.sessao.csrf_hash)
        ):
            raise ErroConta(403, "csrf_invalido", "Requisição recusada. Recarregue a página.")

    async def logout(self, token: str | None, ip: str, user_agent: str) -> None:
        if not token:
            return
        agora = self.relogio.agora_ms()
        sessao = await self.repo.sessao(hash_token(token))
        if sessao is None or sessao.revogada_em is not None:
            return
        await self.repo.salvar_sessao(replace(sessao, revogada_em=agora, motivo_revogacao="logout"))
        await self.repo.registrar_acesso(sessao.usuario_id, "logout", ip, user_agent, agora)

    # ------------------------------------------------------------------ conta
    async def trocar_senha(self, ctx: Contexto, atual: str, nova: str) -> None:
        if not self.hasher.verificar(ctx.usuario.senha_hash, atual):
            raise ErroConta(422, "senha_atual_incorreta", "A senha atual está incorreta.")
        validar_senha_nova(nova)
        agora = self.relogio.agora_ms()
        await self.repo.salvar_usuario(replace(ctx.usuario, senha_hash=self.hasher.gerar(nova)))
        await self.repo.revogar_sessoes(
            ctx.usuario.id, agora, "senha_alterada", exceto=ctx.sessao.token_hash
        )
        await self.repo.registrar_acesso(
            ctx.usuario.id, "senha_alterada", ctx.sessao.ip, ctx.sessao.user_agent, agora
        )

    async def preferencias(
        self, ctx: Contexto, modo: Modo | None, layout: dict[str, Any] | None
    ) -> Usuario:
        usuario = ctx.usuario
        if modo is Modo.AVANCADO and not pode_modo_avancado(ctx):
            raise ErroConta(
                403, "recurso_nao_incluido", "O modo avançado não está incluído no seu plano."
            )
        if layout is not None:
            tamanho = len(json.dumps(layout, ensure_ascii=False).encode())
            if tamanho > LAYOUT_MAXIMO_BYTES:
                raise ErroConta(422, "layout_grande", "As configurações salvas são grandes demais.")
            usuario = replace(usuario, layout=layout)
        if modo is not None:
            usuario = replace(usuario, modo=modo)
        await self.repo.salvar_usuario(usuario)
        return usuario
