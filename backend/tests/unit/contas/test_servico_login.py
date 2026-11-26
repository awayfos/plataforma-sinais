import asyncio
from collections.abc import Awaitable
from dataclasses import replace
from typing import Any

import pytest

from sinais.contas.modelos import StatusUsuario
from sinais.contas.servico import ErroConta, ParametrosContas

from .dubles import T0, M, S, admin, ambiente, cliente, codigo_totp


def rodar[T](c: Awaitable[T]) -> T:
    async def _() -> T:
        return await c

    return asyncio.run(_())


def erro(c: Awaitable[Any]) -> ErroConta:
    with pytest.raises(ErroConta) as e:
        rodar(c)
    return e.value


def test_login_ok_cria_sessao_com_hash_e_registra_acesso() -> None:
    async def caso() -> None:
        amb = ambiente()
        u = await cliente(amb)
        r = await amb.servico.login(" ANA@Exemplo.com ", "senha-forte-123", None, "1.2.3.4", "ua")
        assert r.usuario.id == u.id
        assert r.token and r.csrf and r.token != r.csrf
        assert await amb.repo.sessao(r.token) is None  # nunca guarda o token puro
        ctx = await amb.servico.autenticar(r.token)
        assert ctx.usuario.id == u.id
        assert ctx.sessao.ip == "1.2.3.4"
        assert [a.evento for a in await amb.repo.listar_acessos(u.id, 10)] == ["login"]

    rodar(caso())


def test_senha_errada_e_email_inexistente_respondem_igual() -> None:
    async def caso() -> tuple[ErroConta, ErroConta, int]:
        amb = ambiente()
        await cliente(amb)
        with pytest.raises(ErroConta) as a:
            await amb.servico.login("ana@exemplo.com", "errada-errada", None, "ip", "ua")
        antes = amb.hasher.verificacoes
        with pytest.raises(ErroConta) as b:
            await amb.servico.login("ninguem@exemplo.com", "errada-errada", None, "ip", "ua")
        # o e-mail inexistente também gasta uma verificação de hash (mesmo tempo)
        return a.value, b.value, amb.hasher.verificacoes - antes

    a, b, verificacoes = rodar(caso())
    assert (a.status, a.codigo, a.mensagem) == (b.status, b.codigo, b.mensagem)
    assert (a.status, a.codigo) == (401, "credenciais_invalidas")
    assert verificacoes == 1


def test_bloqueio_progressivo_vale_inclusive_para_email_inexistente() -> None:
    async def caso() -> None:
        amb = ambiente()
        await cliente(amb)
        for email in ("ana@exemplo.com", "fantasma@exemplo.com"):
            for _ in range(5):
                with pytest.raises(ErroConta) as e:
                    await amb.servico.login(email, "x" * 10, None, f"ip-{email}", "ua")
                assert e.value.status == 401
            with pytest.raises(ErroConta) as e:
                await amb.servico.login(email, "x" * 10, None, f"ip-{email}", "ua")
            assert (e.value.status, e.value.codigo) == (423, "conta_bloqueada")
        # nem a senha certa entra durante o bloqueio, a partir do mesmo IP
        ip = "ip-ana@exemplo.com"
        with pytest.raises(ErroConta) as e:
            await amb.servico.login("ana@exemplo.com", "senha-forte-123", None, ip, "ua")
        assert e.value.status == 423
        amb.relogio.avancar(61 * S)
        r = await amb.servico.login("ana@exemplo.com", "senha-forte-123", None, ip, "ua")
        assert r.token

    rodar(caso())


def test_sucesso_zera_falhas() -> None:
    async def caso() -> None:
        amb = ambiente()
        await cliente(amb)
        for _ in range(4):
            with pytest.raises(ErroConta):
                await amb.servico.login("ana@exemplo.com", "x" * 10, None, "ip", "ua")
        await amb.servico.login("ana@exemplo.com", "senha-forte-123", None, "ip", "ua")
        for _ in range(4):
            with pytest.raises(ErroConta) as e:
                await amb.servico.login("ana@exemplo.com", "x" * 10, None, "ip", "ua")
            assert e.value.status == 401

    rodar(caso())


def test_limite_por_ip_responde_429() -> None:
    async def caso() -> None:
        amb = ambiente()
        for i in range(20):
            with pytest.raises(ErroConta) as e:
                await amb.servico.login(f"u{i}@exemplo.com", "x" * 10, None, "9.9.9.9", "ua")
            assert e.value.status == 401
        with pytest.raises(ErroConta) as e:
            await amb.servico.login("outro@exemplo.com", "x" * 10, None, "9.9.9.9", "ua")
        assert (e.value.status, e.value.codigo) == (429, "muitas_tentativas")
        amb.relogio.avancar(M)
        with pytest.raises(ErroConta) as e:
            await amb.servico.login("outro@exemplo.com", "x" * 10, None, "9.9.9.9", "ua")
        assert e.value.status == 401

    rodar(caso())


def test_conta_bloqueada_423_so_com_senha_certa_e_desativada_401() -> None:
    async def caso() -> None:
        amb = ambiente()
        u = await cliente(amb)
        await amb.repo.salvar_usuario(replace(u, status=StatusUsuario.BLOQUEADO))
        with pytest.raises(ErroConta) as e:
            await amb.servico.login("ana@exemplo.com", "x" * 10, None, "ip", "ua")
        assert e.value.status == 401
        with pytest.raises(ErroConta) as e:
            await amb.servico.login("ana@exemplo.com", "senha-forte-123", None, "ip", "ua")
        assert (e.value.status, e.value.codigo) == (423, "conta_bloqueada")
        await amb.repo.salvar_usuario(replace(u, status=StatusUsuario.DESATIVADO))
        with pytest.raises(ErroConta) as e:
            await amb.servico.login("ana@exemplo.com", "senha-forte-123", None, "ip", "ua")
        assert (e.value.status, e.value.codigo) == (401, "credenciais_invalidas")

    rodar(caso())


def test_admin_exige_totp_e_recusa_reuso() -> None:
    async def caso() -> None:
        amb = ambiente()
        await admin(amb)
        senha = "senha-admin-123"
        with pytest.raises(ErroConta) as e:
            await amb.servico.login("admin@exemplo.com", senha, None, "ip", "ua")
        assert (e.value.status, e.value.codigo) == (401, "totp_necessario")
        with pytest.raises(ErroConta) as e:
            await amb.servico.login("admin@exemplo.com", senha, "000000", "ip", "ua")
        assert (e.value.status, e.value.codigo) == (401, "totp_invalido")
        codigo = codigo_totp(T0)
        r = await amb.servico.login("admin@exemplo.com", senha, codigo, "ip", "ua")
        assert r.usuario.papel == "admin"
        with pytest.raises(ErroConta) as e:  # mesmo código de novo: replay
            await amb.servico.login("admin@exemplo.com", senha, codigo, "ip", "ua")
        assert e.value.codigo == "totp_invalido"
        amb.relogio.avancar(30 * S)
        r2 = await amb.servico.login(
            "admin@exemplo.com", senha, codigo_totp(T0 + 30 * S), "ip", "ua"
        )
        assert r2.token

    rodar(caso())


def test_totp_necessario_nao_revela_se_a_senha_errada() -> None:
    async def caso() -> None:
        amb = ambiente()
        await admin(amb)
        with pytest.raises(ErroConta) as e:
            await amb.servico.login("admin@exemplo.com", "errada-errada", None, "ip", "ua")
        assert e.value.codigo == "credenciais_invalidas"

    rodar(caso())


def test_uma_sessao_por_conta_login_novo_derruba_a_anterior() -> None:
    async def caso() -> None:
        amb = ambiente()
        await cliente(amb)
        a = await amb.servico.login("ana@exemplo.com", "senha-forte-123", None, "ip", "ua")
        b = await amb.servico.login("ana@exemplo.com", "senha-forte-123", None, "ip2", "ua")
        with pytest.raises(ErroConta) as e:
            await amb.servico.autenticar(a.token)
        assert (e.value.status, e.value.codigo) == (401, "sessao_invalida")
        assert (await amb.servico.autenticar(b.token)).sessao.ip == "ip2"

    rodar(caso())


def test_limite_de_sessoes_configuravel() -> None:
    async def caso() -> None:
        amb = ambiente(ParametrosContas(sessoes_simultaneas=2))
        await cliente(amb)
        tokens = []
        for _ in range(3):
            r = await amb.servico.login("ana@exemplo.com", "senha-forte-123", None, "ip", "ua")
            tokens.append(r.token)
            amb.relogio.avancar(1)  # sessões criadas em instantes distintos: a mais antiga sai
        with pytest.raises(ErroConta):
            await amb.servico.autenticar(tokens[0])
        for t in tokens[1:]:
            await amb.servico.autenticar(t)

    rodar(caso())


def test_atacante_de_outro_ip_nao_bloqueia_o_dono_da_conta() -> None:
    async def caso() -> None:
        amb = ambiente()
        await admin(amb)
        for _ in range(6):
            with pytest.raises(ErroConta):
                await amb.servico.login("admin@exemplo.com", "x" * 10, None, "6.6.6.6", "ua")
        with pytest.raises(ErroConta) as e:
            await amb.servico.login("admin@exemplo.com", "x" * 10, None, "6.6.6.6", "ua")
        assert e.value.status == 423
        r = await amb.servico.login(
            "admin@exemplo.com", "senha-admin-123", codigo_totp(T0), "10.0.0.1", "ua"
        )
        assert r.token

    asyncio.run(caso())


def test_teto_global_por_email_bloqueia_ataque_distribuido_sem_enumeracao() -> None:
    from sinais.contas.limites import PoliticaLogin

    async def caso() -> None:
        pol = PoliticaLogin(falhas_globais_email=8, bloqueio_global_s=900)
        amb = ambiente(ParametrosContas(politica=pol))
        await cliente(amb)
        for email in ("ana@exemplo.com", "fantasma@exemplo.com"):
            for i in range(8):
                with pytest.raises(ErroConta) as e:
                    await amb.servico.login(email, "x" * 10, None, f"ip{i}-{email}", "ua")
                assert e.value.status == 401
            with pytest.raises(ErroConta) as e:
                await amb.servico.login(email, "senha-forte-123", None, "ip-novo", "ua")
            assert (e.value.status, e.value.codigo) == (423, "conta_bloqueada")
        amb.relogio.avancar(901 * S)
        assert (await amb.servico.login("ana@exemplo.com", "senha-forte-123", None, "i", "u")).token

    asyncio.run(caso())


def test_hash_de_senha_roda_fora_do_laco_e_com_limite_de_paralelismo() -> None:
    import threading
    import time

    class HasherLento:
        def __init__(self) -> None:
            self.threads: set[int] = set()
            self.ativos = 0
            self.maximo = 0
            self._trava = threading.Lock()

        def _trabalho(self) -> None:
            with self._trava:
                self.ativos += 1
                self.maximo = max(self.maximo, self.ativos)
            self.threads.add(threading.get_ident())
            time.sleep(0.02)
            with self._trava:
                self.ativos -= 1

        def gerar(self, senha: str) -> str:
            return "h:" + senha

        def verificar(self, hash_: str, senha: str) -> bool:
            self._trabalho()
            return hash_ == "h:" + senha

        def precisa_rehash(self, hash_: str) -> bool:
            return False

    async def caso() -> HasherLento:
        amb = ambiente(ParametrosContas(hash_paralelo=2, sessoes_simultaneas=10))
        h = HasherLento()
        amb.servico.hasher = h
        await cliente(amb)
        await asyncio.gather(
            *(
                amb.servico.login("ana@exemplo.com", "senha-forte-123", None, f"i{i}", "u")
                for i in range(6)
            )
        )
        return h

    h = asyncio.run(caso())
    assert threading.get_ident() not in h.threads
    assert h.maximo == 2
