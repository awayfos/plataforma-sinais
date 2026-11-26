"""Simulação das situações com a regra da Exnova e preços de 1 s (design §9b.1).

- Entrada num segundo inteiro entre decisão + 2 s e decisão + 10 s. O segundo é sorteado por
  um hash do próprio instante da decisão (``deslocamento_entrada``): o resultado de um evento não
  depende de quais outros eventos estão no lote, então reprocessar mês a mês dá o mesmo resultado
  que a série inteira (exigência da confirmação em meses novos).
- Vencimento alinhado ao relógio (``modelos.rotulos.vencimentos``). A situação só vale se
  ``vencimento − decisão ≤ grade`` (15 min: entre 5 e 15 min até o vencimento) e a entrada cair
  até o prazo de compra; senão ``FORA_DA_JANELA``.
- Recusa (``FORA_DA_TOLERANCIA``) se |preço na entrada − preço na decisão| > 0,5 × ATR14(1m) da
  decisão (como ``backtest.simulador.simular``; ATR ou preço da decisão ausente não bloqueia).
- Preço = fechamento do candle de 1 s que termina no instante (``SeriePrecos``); sem preço:
  ``SEM_DADO``. Empate = ``TIE``. Um sinal ativo por vencimento: eventos com decisão antes do
  vencimento de uma operação aceita viram ``IGNORADO_ATIVO``. Recusas e ``SEM_DADO`` não ocupam.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from sinais.backtest.precos import SeriePrecos
from sinais.corretoras.regras import RegraVencimento
from sinais.modelos.rotulos import vencimentos
from sinais.situacoes.parametros import EXECUCAO, Execucao

LIQUIDADAS = ("WIN", "LOSS", "TIE")
COLUNAS_OPERACAO = [
    "decisao",
    "direcao",
    "entrada_t",
    "vencimento_t",
    "tempo_restante_s",
    "preco_decisao",
    "preco_entrada",
    "preco_vencimento",
    "apertado",
    "resultado",
]
_MASCARA = np.uint64(0xFFFFFFFFFFFFFFFF)


def _splitmix64(x: np.ndarray) -> np.ndarray:
    with np.errstate(over="ignore"):
        z = (x + np.uint64(0x9E3779B97F4A7C15)) & _MASCARA
        z = ((z ^ (z >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)) & _MASCARA
        z = ((z ^ (z >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)) & _MASCARA
        return np.asarray(z ^ (z >> np.uint64(31)))


def deslocamento_entrada(
    decisoes: np.ndarray, semente: int, minimo_s: int = 2, maximo_s: int = 10
) -> np.ndarray:
    """Segundos entre a decisão e a entrada, em ``[minimo_s, maximo_s]``, por evento."""
    chave = np.asarray(decisoes, dtype="int64") // 1000
    with np.errstate(over="ignore"):
        x = chave.astype("uint64") ^ (np.uint64(semente) * np.uint64(0xD1B54A32D192ED03))
    largura = np.uint64(maximo_s - minimo_s + 1)
    return (_splitmix64(x) % largura).astype("int64") + minimo_s


def janela_valida(decisoes: np.ndarray, regra: RegraVencimento) -> tuple[np.ndarray, np.ndarray]:
    """(vencimento mirado na decisão, se ``vencimento − decisão ≤ grade``)."""
    d = np.asarray(decisoes, dtype="int64")
    alvo = vencimentos(d, regra)
    return alvo, (alvo - d) <= regra.grade_ms


def simular_eventos(
    eventos: pd.DataFrame,
    precos_1s: SeriePrecos,
    regra: RegraVencimento,
    atr_por_decisao: pd.Series,
    execucao: Execucao = EXECUCAO,
    sem_sobreposicao: bool = True,
) -> pd.DataFrame:
    """Uma linha por evento (``decisao``, ``direcao``), em ordem de decisão."""
    ev = eventos.sort_values("decisao", kind="stable")
    d = ev["decisao"].to_numpy(dtype="int64")
    direcao = ev["direcao"].to_numpy(dtype="int64")
    alvo, valida = janela_valida(d, regra)
    desloc = deslocamento_entrada(
        d, execucao.semente, execucao.entrada_min_s, execucao.entrada_max_s
    )
    entrada = d + 1000 * desloc
    dentro = valida & (entrada <= alvo - regra.corte_ms - 1)
    p_dec = precos_1s.precos_em(d)
    p_ent = precos_1s.precos_em(entrada)
    p_venc = precos_1s.precos_em(alvo)
    atr = atr_por_decisao.reindex(d).to_numpy(dtype="float64")
    afastou = np.abs(p_ent - p_dec) > execucao.tolerancia_atr * atr  # NaN → False
    margem = (p_venc - p_ent) * direcao
    resultado = np.where(margem > 0, "WIN", np.where(margem < 0, "LOSS", "TIE")).astype(object)
    resultado[afastou] = "FORA_DA_TOLERANCIA"
    resultado[np.isnan(p_ent) | np.isnan(p_venc)] = "SEM_DADO"
    resultado[~dentro] = "FORA_DA_JANELA"
    if sem_sobreposicao:
        ativo_ate = np.iinfo("int64").min
        for k in range(len(d)):
            if d[k] < ativo_ate:
                resultado[k] = "IGNORADO_ATIVO"
            elif resultado[k] in LIQUIDADAS:
                ativo_ate = int(alvo[k])
    liquidada = np.isin(resultado, LIQUIDADAS)
    with np.errstate(invalid="ignore"):
        apertado = np.abs(p_venc - p_ent) <= execucao.limiar_apertado * p_ent
    return pd.DataFrame(
        {
            "decisao": d,
            "direcao": direcao,
            "entrada_t": entrada,
            "vencimento_t": alvo,
            "tempo_restante_s": (alvo - entrada) // 1000,
            "preco_decisao": p_dec,
            "preco_entrada": np.where(
                liquidada | (resultado == "FORA_DA_TOLERANCIA"), p_ent, np.nan
            ),
            "preco_vencimento": np.where(liquidada, p_venc, np.nan),
            "apertado": apertado & liquidada,
            "resultado": resultado.astype(str),
        },
        columns=COLUNAS_OPERACAO,
    )
