import asyncio

import pytest

from sinais.contas.modelos import Papel, StatusUsuario
from sinais.contas.servico import ErroConta
from sinais.processos.criar_admin import criar_admin

from ..contas.dubles import SEGREDO_TOTP, T0, HasherFalso, TotpFalso, ambiente, codigo_totp


def test_cria_admin_com_totp_cifrado_e_devolve_uri() -> None:
    async def caso() -> None:
        amb = ambiente()
        args = (amb.repo, HasherFalso(), TotpFalso(), amb.cifra, amb.relogio)
        uri = await criar_admin(*args, " Root@Exemplo.com ", "Root", "senha-admin-123")
        assert uri.startswith("otpauth://") and "root@exemplo.com" in uri
        u = await amb.repo.usuario_por_email("root@exemplo.com")
        assert u is not None and u.papel is Papel.ADMIN
        assert u.totp_cifrado and SEGREDO_TOTP not in u.totp_cifrado
        assert amb.cifra.decifrar(u.totp_cifrado, f"usuario:{u.id}") == SEGREDO_TOTP
        r = await amb.servico.login(
            "root@exemplo.com", "senha-admin-123", codigo_totp(T0), "i", "u"
        )
        assert r.token

    asyncio.run(caso())


def test_redefine_admin_existente_e_derruba_sessoes() -> None:
    async def caso() -> None:
        amb = ambiente()
        args = (amb.repo, HasherFalso(), TotpFalso(), amb.cifra, amb.relogio)
        await criar_admin(*args, "root@exemplo.com", "Root", "senha-admin-123")
        r = await amb.servico.login(
            "root@exemplo.com", "senha-admin-123", codigo_totp(T0), "i", "u"
        )
        u = await amb.repo.usuario_por_email("root@exemplo.com")
        assert u is not None
        await amb.repo.atualizar_usuario(u.id, {"status": StatusUsuario.BLOQUEADO})
        await criar_admin(*args, "root@exemplo.com", "Root", "outra-senha-456")
        with pytest.raises(ErroConta):
            await amb.servico.autenticar(r.token)
        u2 = await amb.repo.usuario_por_email("root@exemplo.com")
        assert u2 is not None and u2.status is StatusUsuario.ATIVO and u2.totp_ultimo_passo is None

    asyncio.run(caso())


def test_recusa_senha_fraca() -> None:
    amb = ambiente()
    with pytest.raises(ErroConta):
        asyncio.run(
            criar_admin(
                amb.repo,
                HasherFalso(),
                TotpFalso(),
                amb.cifra,
                amb.relogio,
                "a@b.com",
                "A",
                "curta",
            )
        )
