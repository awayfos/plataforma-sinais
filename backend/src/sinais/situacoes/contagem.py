"""Contagem de ocorrências sem rótulo (design §4 e §9b.3), antes de qualquer rodada rotulada.

Conta por variação × espelho × ativo × expiração os sinais que o motor emitiria: sem conflito,
com a janela de compra válida para a entrada sorteada (que não depende de preço) e um por
vencimento. Não olha preço nenhum: é um teto para o n da avaliação (a tolerância de preço e o
``SEM_DADO`` ainda tiram operações). Chave com menos de ``N_MINIMO`` nos meses de teste do
walk-forward fica fora da avaliação confirmatória.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from sinais.corretoras.regras import RegraVencimento
from sinais.situacoes.parametros import ESPELHOS, EXECUCAO, N_MINIMO, VARIACOES, Execucao
from sinais.situacoes.simulacao import deslocamento_entrada, janela_valida


def contar(
    eventos: pd.DataFrame,
    regra: RegraVencimento,
    inicio: int,
    fim: int,
    execucao: Execucao = EXECUCAO,
) -> int:
    ev = eventos[
        ~eventos["conflito"].astype(bool)
        & (eventos["decisao"] >= inicio)
        & (eventos["decisao"] < fim)
    ]
    d = np.sort(ev["decisao"].to_numpy(dtype="int64"))
    alvo, valida = janela_valida(d, regra)
    entrada = d + 1000 * deslocamento_entrada(
        d, execucao.semente, execucao.entrada_min_s, execucao.entrada_max_s
    )
    ok = valida & (entrada <= alvo - regra.corte_ms - 1)
    n, ativo_ate = 0, np.iinfo("int64").min
    for k in np.flatnonzero(ok):
        if d[k] >= ativo_ate:
            n += 1
            ativo_ate = int(alvo[k])
    return n


def tabela_contagem(
    eventos: pd.DataFrame,
    periodos: Mapping[str, tuple[int, int]],
    regras: Mapping[str, RegraVencimento],
    ativos: Sequence[str],
    periodo_corte: str = "teste",
) -> pd.DataFrame:
    """``eventos`` com coluna ``ativo``. Uma linha por chave da grade completa (zeros incluídos)."""
    linhas = []
    grupos = {k: g for k, g in eventos.groupby(["ativo", "variacao", "espelho"])}
    for ativo in ativos:
        for v in VARIACOES:
            for espelho in ESPELHOS:
                g = grupos.get((ativo, v.nome, espelho), eventos.iloc[:0])
                for nome_exp, regra in regras.items():
                    linha: dict[str, object] = {
                        "ativo": ativo, "variacao": v.nome, "espelho": espelho,
                        "expiracao": nome_exp,
                    }  # fmt: skip
                    for nome, (ini, fim) in periodos.items():
                        linha[nome] = contar(g, regra, ini, fim)
                    linhas.append(linha)
    tab = pd.DataFrame(linhas)
    tab["elegivel"] = tab[periodo_corte] >= N_MINIMO
    return tab


def markdown_contagem(tab: pd.DataFrame, periodos: Sequence[str]) -> str:
    cab = "| Ativo | Variação | Espelho | Exp. | " + " | ".join(periodos) + " | Elegível |"
    partes = [cab, "|" + "---|" * (len(periodos) + 5)]
    for x in tab.itertuples(index=False):
        n = " | ".join(str(getattr(x, p)) for p in periodos)
        ok = "sim" if x.elegivel else "não"
        partes.append(f"| {x.ativo} | {x.variacao} | {x.espelho} | {x.expiracao} | {n} | {ok} |")
    return "\n".join(partes)
