"""Sinais por expiração para ``/api/sinais``.

Enquanto nenhum modelo estiver aprovado (sem campeão no registro de modelos), toda expiração
devolve AGUARDAR com ``probabilidade: null`` (contrato v1). Com campeão registrado, continua
AGUARDAR até o motor de sinais ao vivo existir: nunca se mostra uma probabilidade que não
saiu do motor validado.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from sinais.api.esquemas import ExpiracaoRotulo, Sinal

EXPIRACOES: tuple[ExpiracaoRotulo, ...] = ("1m", "5m", "15m", "30m", "60m")
MOTIVO_SEM_MODELO = "Nenhum modelo validado para esta expiração"
MOTIVO_SEM_MOTOR = "Modelo validado, mas o motor de sinais ao vivo ainda não está ativo"

type BuscaCampeao = Callable[[str, str], str | None]


def sinais_para(
    simbolo: str, expiracoes: Sequence[ExpiracaoRotulo], campeao: BuscaCampeao
) -> list[Sinal]:
    saida = []
    for e in expiracoes:
        versao = campeao(simbolo, e)
        saida.append(
            Sinal(
                expiracao=e,
                direcao="AGUARDAR",
                probabilidade=None,
                n_validacao=None,
                motivo=MOTIVO_SEM_MODELO if versao is None else MOTIVO_SEM_MOTOR,
                janela_ate=None,
                invalidacao=None,
                modelo=versao,
            )
        )
    return saida


def campeao_do_registro(pasta: str) -> BuscaCampeao:
    """Versão do campeão de ``sinais.modelos.registro`` (``None`` sem campeão ou sem pasta)."""
    from sinais.modelos.registro import Registro

    registro = Registro(pasta)

    def buscar(simbolo: str, expiracao: str) -> str | None:
        try:
            dados = registro.campeao(simbolo, expiracao)
        except (OSError, ValueError):
            return None
        versao = dados.get("versao") if dados else None
        return str(versao) if versao else None

    return buscar
