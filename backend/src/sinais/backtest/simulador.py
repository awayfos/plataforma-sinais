"""Simulador de operações com as regras de vencimento da corretora.

Cada sinal mira o vencimento calculado no instante da decisão. A entrada acontece em
``decisao + latencia``; se isso passar do prazo de compra, o sinal vira ``FORA_DA_JANELA``.
Com preços de 1 min, o preço de entrada é a abertura do minuto da decisão (o primeiro negócio
depois dela): aproximação otimista em ``latencia``, declarada no relatório.
"""

from __future__ import annotations

import pandas as pd

from sinais.backtest.precos import SeriePrecos
from sinais.core.dominio import Direcao
from sinais.corretoras.regras import RegraVencimento, liquidar

FORA_DA_JANELA = "FORA_DA_JANELA"
SEM_DADO = "SEM_DADO"
IGNORADO_ATIVO = "IGNORADO_ATIVO"


def _teto(t: int, passo: int) -> int:
    return -(-t // passo) * passo


def simular(
    sinais: pd.DataFrame,
    precos: SeriePrecos,
    regra: RegraVencimento,
    latencia_ms: int = 2000,
) -> pd.DataFrame:
    linhas = []
    ativo_ate = -1
    g = precos.granularidade_ms
    for decisao, direcao in sinais.sort_values("decisao")[["decisao", "direcao"]].itertuples(
        index=False
    ):
        decisao = int(decisao)
        alvo = regra.vencimento_para(decisao)
        entrada = decisao + latencia_ms
        t_preco = _teto(decisao, g) if g > 1000 else _teto(entrada, g)
        linha = {
            "decisao": decisao,
            "direcao": int(direcao),
            "entrada_t": entrada,
            "vencimento_t": alvo,
            "preco_entrada": float("nan"),
            "preco_vencimento": float("nan"),
            "margem": float("nan"),
        }
        if decisao < ativo_ate:
            linhas.append({**linha, "resultado": IGNORADO_ATIVO})
            continue
        if entrada > regra.prazo_compra(alvo):
            linhas.append({**linha, "resultado": FORA_DA_JANELA})
            continue
        pe, pv = precos.preco_em(t_preco), precos.preco_em(alvo)
        if pe is None or pv is None:
            linhas.append({**linha, "resultado": SEM_DADO})
            continue
        d = Direcao.COMPRA if direcao > 0 else Direcao.VENDA
        ativo_ate = alvo
        linhas.append(
            {
                **linha,
                "preco_entrada": pe,
                "preco_vencimento": pv,
                "margem": (pv - pe) * (1 if direcao > 0 else -1),
                "resultado": liquidar(d, pe, pv).value,
            }
        )
    colunas = [
        "decisao",
        "direcao",
        "entrada_t",
        "vencimento_t",
        "preco_entrada",
        "preco_vencimento",
        "margem",
        "resultado",
    ]
    return pd.DataFrame(linhas, columns=colunas)
