import math

from sinais.core.dominio import Expiracao
from sinais.modelos.decisao import consolidar
from sinais.modelos.decisao_v2 import ExtrasFiltro, gerar_markdown_v2, meses_ate

from .test_decisao import resultado


def test_meses_ate_inclui_o_fim_e_atravessa_o_ano() -> None:
    assert meses_ate("2025-02", 4) == [(2024, 11), (2024, 12), (2025, 1), (2025, 2)]
    assert meses_ate("2026-10", 24)[0] == (2024, 11)


def test_markdown_v2_tem_principal_apertados_holdout_e_diagnosticos() -> None:
    principal = consolidar({("BTCUSDT", Expiracao.M1): resultado(700, 300, 70, 30)}, 0.86)
    diag = consolidar({("BTCUSDT", Expiracao.M1): resultado(520, 480, 52, 48)}, 0.86)
    texto = gerar_markdown_v2(
        principal,
        {"fs-2 sem filtro": diag},
        {("BTCUSDT", "1m"): ExtrasFiltro([0.3, math.inf], [0.25, 0.0], 0.4, 0.3)},
        {"fonte": "teste"},
    )
    assert "## Resultado do candidato (fs-2 + filtro de apertados)" in texto
    assert "| BTCUSDT | 1m | 1000 | 70.00% |" in texto
    assert "**ligar**" in texto
    assert "fs-2 sem filtro" in texto
    assert "sem direito a aprovação" in texto
    assert "| BTCUSDT | 1m | 1 de 2 | 12.50% | 0.300, — | 0.400 | 30.00% |" in texto
    assert "DIAGNÓSTICO" not in texto
    assert "**fonte:** teste" in texto


def test_modo_diagnostico_marca_o_relatorio_inteiro() -> None:
    principal = consolidar({("BTCUSDT", Expiracao.M1): resultado(700, 300, 70, 30)}, 0.86)
    texto = gerar_markdown_v2(principal, {}, {}, {"fonte": "teste"}, diagnostico="entrada ≤ 10 s")
    assert texto.startswith("# DIAGNÓSTICO DE SENSIBILIDADE (sem direito a aprovação)")
    assert "entrada ≤ 10 s" in texto
    assert "Combinações aprovadas" not in texto
    assert "(teria: ligar)" in texto
