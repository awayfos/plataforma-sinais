"""Parâmetros PRÉ-REGISTRADOS do motor de situações.

Fixados em ``docs/laboratorio/2026-11-26-situacoes-pre-registro.md`` antes de qualquer contagem ou
rodada rotulada. Não mudar depois da contagem: qualquer mudança invalida a avaliação confirmatória.
S1 usa os números do design (§4). Cada situação tem no máximo 2 variações (design §9b.7).
"""

from __future__ import annotations

from dataclasses import dataclass

MINUTO_MS = 60_000
JANELA_4H_MIN = 240
N_ATR = 14


@dataclass(frozen=True)
class ParamS1:
    """Exaustão no topo novo (estratégia do cliente; números do design)."""

    janela_min: int = JANELA_4H_MIN
    pressao_rompimento: float = 0.55  # fundo: ≤ 0,45
    pressao_fraca: float = 0.50  # fundo: > 0,50
    candles_fraqueza: int = 3
    minimo_fracos: int = 2
    confirmacao_min: int = 10


@dataclass(frozen=True)
class ParamS2:
    """Falso rompimento de região com toques."""

    toques_min: int = 3
    janela_toques_min: int = JANELA_4H_MIN
    volta_max_candles: int = 3
    tolerancia_atr: float = 0.5  # fusão de pivôs de 1m em um nível (como analise.regioes)
    k_pivo: int = 3


@dataclass(frozen=True)
class ParamS3:
    """Rompimento com força + reteste. S3: ≥ 3 toques; S3b: ≥ 4 (região gasta)."""

    toques_min: int = 3
    janela_toques_min: int = JANELA_4H_MIN
    volume_rel_min: float = 1.5
    pressao_min: float = 0.60  # baixa: ≤ 0,40
    reteste_max_min: int = 15
    proximidade_atr: float = 0.25
    tolerancia_atr: float = 0.5
    k_pivo: int = 3


@dataclass(frozen=True)
class ParamS4:
    """Reteste após BOS no 5m com candle de rejeição (engolfo ou pin bar) no 1m."""

    k_pivo_5m: int = 3
    janela_min: int = 60
    proximidade_atr: float = 0.25


@dataclass(frozen=True)
class ParamS5:
    """CHoCH no 5m após tendência de 15m com ADX alto e divergência de RSI no 5m."""

    k_pivo_5m: int = 3
    adx_min: float = 25.0
    idade_max_pivo_5m: int = 36  # candles de 5m (3 h) entre o pivô mais novo e o CHoCH


@dataclass(frozen=True)
class ParamS6:
    """Rejeição repetida na máxima/mínima de 4 h em 15m. S6: novo toque é o 4º ou mais;
    S6a: 2º ou 3º toque (região ainda forte)."""

    janela_15m: int = 16  # 4 h
    tolerancia_atr15: float = 0.15
    toques_previos_min: int = 3
    toques_previos_max: int = 99
    pressao_max: float = 0.50  # fundo: > 0,50


@dataclass(frozen=True)
class ParamS7:
    """Topo/fundo de 15m com divergência RSI/MACD confirmada por inversão de pressão."""

    k_pivo_15m: int = 2
    distancia_max_pivos_15m: int = 32  # 8 h entre os dois pivôs
    janela_confirmacao_min: int = 15
    candles_pressao: int = 5
    pressao_max: float = 0.45  # fundo: ≥ 0,55
    distancia_max_atr15: float = 1.0


@dataclass(frozen=True)
class ParamS8:
    """Extremo de lateralização em 15m: toque e rejeição na faixa de 4 h com ADX baixo."""

    janela_15m: int = 16
    adx_max: float = 20.0
    largura_min_atr15: float = 2.0
    largura_max_atr15: float = 8.0
    faixa_extremo: float = 0.10  # fração da largura
    pressao_max: float = 0.50  # fundo: > 0,50


Parametros = ParamS1 | ParamS2 | ParamS3 | ParamS4 | ParamS5 | ParamS6 | ParamS7 | ParamS8


@dataclass(frozen=True)
class Variacao:
    nome: str
    situacao: str
    parametros: Parametros


VARIACOES: tuple[Variacao, ...] = (
    Variacao("S1", "S1", ParamS1()),
    Variacao("S2", "S2", ParamS2()),
    Variacao("S3", "S3", ParamS3()),
    Variacao("S3b", "S3", ParamS3(toques_min=4)),
    Variacao("S4", "S4", ParamS4()),
    Variacao("S5", "S5", ParamS5()),
    Variacao("S6", "S6", ParamS6()),
    Variacao("S6a", "S6", ParamS6(toques_previos_min=1, toques_previos_max=2)),
    Variacao("S7", "S7", ParamS7()),
    Variacao("S8", "S8", ParamS8()),
)
ESPELHOS = ("topo", "fundo")

# Contexto comum (motor)
CONFLUENCIA_JANELA_MIN = 15
QUEDA_PRESSAO_CANDLES = 5


@dataclass(frozen=True)
class Execucao:
    """Entrada e liquidação (design §9b.1 e Fase 6b §7)."""

    entrada_min_s: int = 2
    entrada_max_s: int = 10
    tolerancia_atr: float = 0.5
    limiar_apertado: float = 1e-4
    semente: int = 7


EXECUCAO = Execucao()
PAYOUT = 0.86

# Avaliação (design §6, §9b e §13.3)
N_MINIMO = 300  # ocorrências / operações decididas nos meses de teste do walk-forward
MARGEM_WILSON = 0.01
FRACAO_MESES = 0.70
MINIMO_OPS_MES = 10  # mês com menos operações decididas conta como abaixo do equilíbrio
N_MINIMO_HOLDOUT = 50
Q_BH = 0.05
N_MINIMO_CONFIRMACAO = 100
LINHAS_MINIMAS_B = 1000
LIMIARES_B = (0.01, 0.03, 0.05)  # acima do equilíbrio; escolhido no mês de calibração
MINIMO_CALIBRACAO_B = 30
DOBRAS_CV_B = 3
ALFA_B_SUPERA_A = 0.05
TREINO_MESES = 6
CALIBRACAO_MESES = 1
HOLDOUT_MESES = 3
EMBARGO_MS = 60 * MINUTO_MS
