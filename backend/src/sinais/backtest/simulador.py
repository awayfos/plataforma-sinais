"""Simulador de operações com as regras de vencimento da corretora.

Cada sinal mira o vencimento calculado no instante da decisão. A entrada acontece em
``decisao + latencia``; se isso passar do prazo de compra, o sinal vira ``FORA_DA_JANELA``.
Com preços de 1 min, o preço de entrada é a abertura do minuto da decisão (o primeiro negócio
depois dela): aproximação otimista em ``latencia``, declarada no relatório.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from sinais.backtest.precos import SeriePrecos
from sinais.core.dominio import Direcao
from sinais.corretoras.regras import RegraVencimento, liquidar

FORA_DA_JANELA = "FORA_DA_JANELA"
FORA_DA_TOLERANCIA = "FORA_DA_TOLERANCIA"
SEM_DADO = "SEM_DADO"
IGNORADO_ATIVO = "IGNORADO_ATIVO"


def _teto(t: int, passo: int) -> int:
    return -(-t // passo) * passo


def simular(
    sinais: pd.DataFrame,
    precos: SeriePrecos,
    regra: RegraVencimento,
    latencia_ms: int = 2000,
    entrada_aleatoria: bool = False,
    semente: int = 0,
    limiar_apertado: float = 1e-4,
    entrada_max_ms: int | None = None,
    tolerancia_atr: float | None = None,
) -> pd.DataFrame:
    """``entrada_aleatoria`` (só com preços de 1 s): a entrada é sorteada, em segundos inteiros,
    entre ``decisao + latencia`` e o prazo de compra (design §13.1). ``apertado`` marca
    operações cuja diferença de preço é menor que ``limiar_apertado`` x preço: ali o preço
    da corretora pode dar o resultado oposto.

    ``entrada_max_ms`` limita o sorteio a ``decisao + entrada_max_ms`` (usuário que entra logo
    após o sinal). ``tolerancia_atr`` (design §12.6): se o preço na entrada se afastou do preço
    da decisão mais que ``tolerancia_atr`` x ``sinais["atr"]``, o usuário não entra
    (``FORA_DA_TOLERANCIA``); ATR ausente não bloqueia. Os dois são opcionais e, por padrão,
    não mudam nada."""
    linhas = []
    ativo_ate = -1
    g = precos.granularidade_ms
    rng = np.random.default_rng(semente)
    ordenados = sinais.sort_values("decisao")
    atrs = (
        ordenados["atr"].to_numpy(dtype="float64")
        if tolerancia_atr is not None
        else np.full(len(ordenados), np.nan)
    )
    pares = ordenados[["decisao", "direcao"]].itertuples(index=False)
    for (decisao, direcao), atr in zip(pares, atrs, strict=True):
        decisao = int(decisao)
        alvo = regra.vencimento_para(decisao)
        entrada = _teto(decisao + latencia_ms, 1000)
        prazo = regra.prazo_compra(alvo)
        if g == 1000 and entrada_aleatoria and entrada <= prazo:
            teto = prazo if entrada_max_ms is None else min(prazo, decisao + entrada_max_ms)
            entrada = int(rng.integers(entrada // 1000, max(teto, entrada) // 1000 + 1)) * 1000
        t_preco = decisao if g > 1000 else entrada
        linha = {
            "decisao": decisao,
            "direcao": int(direcao),
            "entrada_t": entrada,
            "vencimento_t": alvo,
            "preco_entrada": float("nan"),
            "preco_vencimento": float("nan"),
            "margem": float("nan"),
            "apertado": False,
        }
        if decisao < ativo_ate:
            linhas.append({**linha, "resultado": IGNORADO_ATIVO})
            continue
        if g > 1000 and decisao % g:
            # Com preços de 1 min não existe preço no meio do minuto: não simular.
            linhas.append({**linha, "resultado": SEM_DADO})
            continue
        if entrada > prazo:
            linhas.append({**linha, "resultado": FORA_DA_JANELA})
            continue
        pe, pv = precos.preco_em(t_preco), precos.preco_em(alvo)
        if pe is None or pv is None:
            linhas.append({**linha, "resultado": SEM_DADO})
            continue
        if tolerancia_atr is not None and not np.isnan(atr):
            p_decisao = precos.preco_em(decisao)
            if p_decisao is not None and abs(pe - p_decisao) > tolerancia_atr * atr:
                linhas.append({**linha, "preco_entrada": pe, "resultado": FORA_DA_TOLERANCIA})
                continue
        d = Direcao.COMPRA if direcao > 0 else Direcao.VENDA
        ativo_ate = alvo
        linhas.append(
            {
                **linha,
                "preco_entrada": pe,
                "preco_vencimento": pv,
                "margem": (pv - pe) * (1 if direcao > 0 else -1),
                "apertado": abs(pv - pe) <= limiar_apertado * pe,
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
        "apertado",
        "resultado",
    ]
    return pd.DataFrame(linhas, columns=colunas)
