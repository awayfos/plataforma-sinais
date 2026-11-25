"""Processo da API (FastAPI + Uvicorn).

Execução: ``python -m sinais.processos.api`` (escuta em 0.0.0.0:8000 dentro do contêiner; o
Compose publica só em 127.0.0.1:8000).
"""

from __future__ import annotations

from typing import Any


def montar_servicos() -> Any:  # pragma: no cover - ligação de I/O
    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import create_async_engine

    from sinais.api.config import carregar_configuracao_api
    from sinais.api.eventos_redis import fonte_redis
    from sinais.api.servicos import Servicos
    from sinais.api.sinais_ao_vivo import campeao_do_registro
    from sinais.contas.admin import ServicoAdmin
    from sinais.contas.seguranca import CifraSegredos
    from sinais.contas.senhas import HasherArgon2
    from sinais.contas.servico import ParametrosContas, ServicoContas
    from sinais.contas.totp import TotpPyotp
    from sinais.core.config import carregar_configuracao
    from sinais.core.dominio import ATIVOS_V1
    from sinais.core.tempo import RelogioSistema
    from sinais.logs import configurar_logs
    from sinais.persistencia.analises import ArmazemAnalisesRedis
    from sinais.persistencia.consultas_mercado import ConsultasMercadoPg
    from sinais.persistencia.limites_redis import ContadorRedis
    from sinais.persistencia.repositorio_contas_pg import RepositorioContasPg
    from sinais.persistencia.url import url_async

    cfg = carregar_configuracao()
    api = carregar_configuracao_api()
    configurar_logs(cfg.nivel_log)
    engine = create_async_engine(url_async(cfg.database_url.get_secret_value()), pool_pre_ping=True)
    redis = Redis.from_url(cfg.redis_url.get_secret_value(), decode_responses=True)
    hora = 3_600_000
    contas = ServicoContas(
        RepositorioContasPg(engine),
        HasherArgon2(),
        TotpPyotp(),
        CifraSegredos.de_base64(api.chave_cifra.get_secret_value()),
        ContadorRedis(redis),
        RelogioSistema(),
        ParametrosContas(
            sessao_duracao_ms=api.sessao_horas * hora,
            sessao_ociosa_ms=api.sessao_ociosa_horas * hora,
            sessoes_simultaneas=api.sessoes_simultaneas,
        ),
    )
    return Servicos(
        contas=contas,
        admin=ServicoAdmin(contas, [a.simbolo for a in ATIVOS_V1]),
        mercado=ConsultasMercadoPg(engine),
        analises=ArmazemAnalisesRedis(redis),
        campeao=campeao_do_registro(api.registro_modelos),
        cookie_seguro=api.cookie_seguro,
        ws_verificacao_s=api.ws_verificacao_s,
        origens_permitidas=api.origens_permitidas,
        confiar_proxy=api.confiar_proxy,
        documentacao=api.documentacao,
        fonte_eventos=fonte_redis(redis),
    )


def criar() -> Any:  # pragma: no cover - fábrica do uvicorn
    from sinais.api.app import criar_app

    return criar_app(montar_servicos())


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(
        "sinais.processos.api:criar",
        factory=True,
        host="0.0.0.0",  # noqa: S104 - dentro do contêiner; o Compose publica só em 127.0.0.1
        port=8000,
        proxy_headers=False,
        server_header=False,
        log_config=None,
    )
