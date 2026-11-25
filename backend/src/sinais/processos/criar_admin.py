"""Cria (ou redefine) um administrador com 2FA e imprime a URI de provisionamento TOTP.

Uso: ``python -m sinais.processos.criar_admin --email admin@exemplo.com [--nome Admin]``.
A senha vem de ``SINAIS_ADMIN_SENHA`` ou é pedida no terminal (nunca por argumento, que
ficaria no histórico do shell). A URI contém o segredo: mostre-a só para quem vai cadastrar
o autenticador.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import sys
from dataclasses import replace

from sinais.contas.modelos import NovoUsuario, Papel, StatusUsuario
from sinais.contas.repositorio import RepositorioContas
from sinais.contas.seguranca import CifraSegredos
from sinais.contas.senhas import Hasher
from sinais.contas.servico import ErroConta, normalizar_email, validar_senha_nova
from sinais.contas.totp import VerificadorTotp
from sinais.core.tempo import Relogio


async def criar_admin(
    repo: RepositorioContas,
    hasher: Hasher,
    totp: VerificadorTotp,
    cifra: CifraSegredos,
    relogio: Relogio,
    email: str,
    nome: str,
    senha: str,
) -> str:
    """Cria o admin (ou, se já existir, redefine senha e segredo TOTP). Devolve a URI TOTP."""
    email = normalizar_email(email)
    validar_senha_nova(senha)
    segredo = totp.novo_segredo()
    cifrado = cifra.cifrar(segredo)
    existente = await repo.usuario_por_email(email)
    agora = relogio.agora_ms()
    if existente is None:
        await repo.criar_usuario(
            NovoUsuario(email, nome, Papel.ADMIN, hasher.gerar(senha), agora, totp_cifrado=cifrado)
        )
    else:
        await repo.salvar_usuario(
            replace(
                existente,
                papel=Papel.ADMIN,
                status=StatusUsuario.ATIVO,
                senha_hash=hasher.gerar(senha),
                totp_cifrado=cifrado,
                totp_ultimo_passo=None,
            )
        )
        await repo.revogar_sessoes(existente.id, agora, "admin_redefinido")
    return totp.uri(segredo, email)


async def principal(argv: list[str] | None = None) -> int:  # pragma: no cover - ligação de I/O
    from sqlalchemy.ext.asyncio import create_async_engine

    from sinais.api.config import carregar_configuracao_api
    from sinais.contas.senhas import HasherArgon2
    from sinais.contas.totp import TotpPyotp
    from sinais.core.config import carregar_configuracao
    from sinais.core.tempo import RelogioSistema
    from sinais.persistencia.repositorio_contas_pg import RepositorioContasPg
    from sinais.persistencia.url import url_async

    p = argparse.ArgumentParser(description="Cria um administrador com 2FA (TOTP).")
    p.add_argument("--email", required=True)
    p.add_argument("--nome", default="Administrador")
    args = p.parse_args(argv)
    senha = os.environ.get("SINAIS_ADMIN_SENHA") or getpass.getpass("Senha do admin: ")
    cfg = carregar_configuracao()
    api = carregar_configuracao_api()
    engine = create_async_engine(url_async(cfg.database_url.get_secret_value()))
    try:
        uri = await criar_admin(
            RepositorioContasPg(engine),
            HasherArgon2(),
            TotpPyotp(),
            CifraSegredos.de_base64(api.chave_cifra.get_secret_value()),
            RelogioSistema(),
            args.email,
            args.nome,
            senha,
        )
    except ErroConta as erro:
        print(erro.mensagem, file=sys.stderr)
        return 2
    finally:
        await engine.dispose()
    print(uri)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(asyncio.run(principal()))
