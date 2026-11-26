"""Liquidação de um sinal: o registro que a área de sinais mostra (design §9c.2).

``VENDA · BTCUSDT · 15 min``, entrada (instante e preço que a IA mandou), vencimento, preço final
e WIN/LOSS/EMPATE pela regra da Exnova. Preço final = fechamento do candle de 1 s que termina no
vencimento (design §12.8); sem preço: ``SEM_DADO``, fora das estatísticas de acerto.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from sinais.backtest.precos import SeriePrecos
from sinais.core.dominio import Direcao
from sinais.corretoras.regras import Resultado, liquidar

_NOME = {Resultado.WIN: "WIN", Resultado.LOSS: "LOSS", Resultado.TIE: "EMPATE"}


@dataclass(frozen=True)
class RegistroSinal:
    ativo: str
    situacao: str
    variacao: str
    direcao: str  # "COMPRA" | "VENDA"
    expiracao_min: int
    entrada_t: int
    preco_entrada: float
    vencimento_t: int
    preco_final: float | None
    resultado: str  # "WIN" | "LOSS" | "EMPATE" | "SEM_DADO"

    @property
    def titulo(self) -> str:
        return f"{self.direcao} · {self.ativo} · {self.expiracao_min} min"


def liquidar_sinal(
    ativo: str,
    situacao: str,
    variacao: str,
    direcao: int,
    expiracao_min: int,
    entrada_t: int,
    preco_entrada: float,
    vencimento_t: int,
    precos_1s: SeriePrecos,
) -> RegistroSinal:
    final = precos_1s.preco_em(vencimento_t)
    d = Direcao.COMPRA if direcao > 0 else Direcao.VENDA
    resultado = "SEM_DADO" if final is None else _NOME[liquidar(d, preco_entrada, final)]
    return RegistroSinal(
        ativo=ativo,
        situacao=situacao,
        variacao=variacao,
        direcao="COMPRA" if direcao > 0 else "VENDA",
        expiracao_min=expiracao_min,
        entrada_t=int(entrada_t),
        preco_entrada=float(preco_entrada),
        vencimento_t=int(vencimento_t),
        preco_final=final,
        resultado=resultado,
    )


def registros_de(
    ops: pd.DataFrame,
    ativo: str,
    situacao: str,
    variacao: str,
    expiracao_min: int,
    precos_1s: SeriePrecos,
) -> list[RegistroSinal]:
    """Registros das operações liquidadas de ``simulacao.simular_eventos``."""
    liquidadas = ops[ops["resultado"].isin(["WIN", "LOSS", "TIE"])]
    return [
        liquidar_sinal(
            ativo, situacao, variacao, int(x.direcao), expiracao_min, int(x.entrada_t),
            float(x.preco_entrada), int(x.vencimento_t), precos_1s,
        )
        for x in liquidadas.itertuples(index=False)
    ]  # fmt: skip
