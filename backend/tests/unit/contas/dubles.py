"""Dublês e fábricas para os testes de contas."""

from __future__ import annotations

from dataclasses import dataclass

from sinais.contas.limites import ContadorMemoria
from sinais.contas.memoria import RepositorioContasMemoria
from sinais.contas.modelos import NovoPlano, NovoUsuario, Papel, Plano, Recursos, Usuario
from sinais.contas.seguranca import CifraSegredos
from sinais.contas.servico import ParametrosContas, ServicoContas
from sinais.core.tempo import RelogioFixo

T0 = 1795575600000
S = 1000
M = 60_000
D = 86_400_000
SEGREDO_TOTP = "JBSWY3DPEHPK3PXP"
TODOS = Recursos(("BTCUSDT", "ETHUSDT"), ("1m", "5m", "15m", "30m", "60m"), True, True)
SO_BTC = Recursos(("BTCUSDT",), ("1m", "5m"), False, False)


class HasherFalso:
    """Hash reversível só para testes: o serviço nunca deve depender do formato."""

    def __init__(self) -> None:
        self.verificacoes = 0

    def gerar(self, senha: str) -> str:
        return "h:" + senha

    def verificar(self, hash_: str, senha: str) -> bool:
        self.verificacoes += 1
        return hash_ == "h:" + senha

    def precisa_rehash(self, hash_: str) -> bool:
        return False


def codigo_totp(agora_ms: int, delta: int = 0) -> str:
    return f"{(agora_ms // 30_000 + delta) % 1_000_000:06d}"


class TotpFalso:
    def novo_segredo(self) -> str:
        return SEGREDO_TOTP

    def passo_valido(self, segredo: str, codigo: str, agora_ms: int) -> int | None:
        if segredo != SEGREDO_TOTP:
            return None
        for delta in (-1, 0, 1):
            if codigo == codigo_totp(agora_ms, delta):
                return agora_ms // 30_000 + delta
        return None

    def uri(self, segredo: str, email: str) -> str:
        return f"otpauth://totp/Sinais:{email}?secret={segredo}"


@dataclass
class Ambiente:
    repo: RepositorioContasMemoria
    relogio: RelogioFixo
    contador: ContadorMemoria
    hasher: HasherFalso
    cifra: CifraSegredos
    servico: ServicoContas


def ambiente(params: ParametrosContas | None = None) -> Ambiente:
    repo = RepositorioContasMemoria()
    relogio = RelogioFixo(T0)
    contador = ContadorMemoria(relogio)
    hasher = HasherFalso()
    cifra = CifraSegredos(bytes(range(32)))
    servico = ServicoContas(
        repo, hasher, TotpFalso(), cifra, contador, relogio, params or ParametrosContas()
    )
    return Ambiente(repo, relogio, contador, hasher, cifra, servico)


async def plano(amb: Ambiente, recursos: Recursos = TODOS, nome: str = "Completo") -> Plano:
    existente = await amb.repo.plano_por_nome(nome)
    if existente:
        return existente
    return await amb.repo.criar_plano(NovoPlano(nome, 30, 9900, recursos, True))


async def cliente(
    amb: Ambiente,
    email: str = "ana@exemplo.com",
    senha: str = "senha-forte-123",
    recursos: Recursos | None = TODOS,
    fim: int = T0 + 30 * D,
) -> Usuario:
    u = await amb.repo.criar_usuario(
        NovoUsuario(email, "Ana", Papel.CLIENTE, "h:" + senha, amb.relogio.agora_ms())
    )
    if recursos is not None:
        p = await plano(amb, recursos, nome="Plano " + ",".join(recursos.ativos))
        await amb.repo.criar_assinatura(u.id, p.id, T0 - D, fim, "manual", T0 - D)
    return u


async def admin(amb: Ambiente, email: str = "admin@exemplo.com") -> Usuario:
    return await amb.repo.criar_usuario(
        NovoUsuario(
            email,
            "Admin",
            Papel.ADMIN,
            "h:senha-admin-123",
            amb.relogio.agora_ms(),
            totp_cifrado=amb.cifra.cifrar(SEGREDO_TOTP),
        )
    )
