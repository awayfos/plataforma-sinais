"""Registro de modelos em arquivos (ADR-09): versões, métricas e o campeão de cada combinação.

Promoção só com aprovação nos critérios de validação e taxa fora da amostra acima da do
campeão atual (champion/challenger).
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import joblib
from scipy.stats import norm


class ErroPromocao(ValueError):
    """O desafiante não pode substituir o campeão."""


class Registro:
    def __init__(self, pasta: Path | str) -> None:
        self._pasta = Path(pasta)

    def _dir(self, ativo: str, expiracao: str, versao: str | None = None) -> Path:
        d = self._pasta / ativo / expiracao
        return d / versao if versao else d

    def salvar(
        self, ativo: str, expiracao: str, versao: str, modelo: Any, metricas: dict[str, Any]
    ) -> Path:
        d = self._dir(ativo, expiracao, versao)
        d.mkdir(parents=True, exist_ok=True)
        joblib.dump(modelo, d / "modelo.joblib")
        (d / "metricas.json").write_text(json.dumps(metricas, ensure_ascii=False, indent=2))
        return d

    def carregar(self, ativo: str, expiracao: str, versao: str) -> Any:
        return joblib.load(self._dir(ativo, expiracao, versao) / "modelo.joblib")

    def _metricas(self, ativo: str, expiracao: str, versao: str) -> dict[str, Any]:
        texto = (self._dir(ativo, expiracao, versao) / "metricas.json").read_text()
        dados: dict[str, Any] = json.loads(texto)
        return dados

    def campeao(self, ativo: str, expiracao: str) -> dict[str, Any] | None:
        arquivo = self._dir(ativo, expiracao) / "campeao.json"
        if not arquivo.exists():
            return None
        dados: dict[str, Any] = json.loads(arquivo.read_text())
        return dados

    def promover(self, ativo: str, expiracao: str, versao: str, alfa: float = 0.05) -> None:
        """Promove se aprovado e melhor que o campeão com significância (teste unilateral de
        duas proporções). As métricas dos dois devem vir do mesmo período fora da amostra."""
        m = self._metricas(ativo, expiracao, versao)
        if not m.get("aprovada"):
            raise ErroPromocao(f"{versao} não passou nos critérios de validação")
        n = int(m.get("wins", 0)) + int(m.get("losses", 0))
        if n == 0 or not math.isfinite(float(m.get("taxa", math.nan))):
            raise ErroPromocao(f"{versao} sem operações decididas")
        atual = self.campeao(ativo, expiracao)
        if atual is not None:
            p = _pvalor_melhor(m["wins"], n, atual["wins"], atual["wins"] + atual["losses"])
            if not p < alfa:
                raise ErroPromocao(
                    f"{versao} não supera o campeão {atual['versao']} com significância "
                    f"(p = {p:.3f})"
                )
        (self._dir(ativo, expiracao) / "campeao.json").write_text(
            json.dumps(
                {"versao": versao, "taxa": m["taxa"], "wins": m["wins"], "losses": m["losses"]}
            )
        )


def _pvalor_melhor(w1: int, n1: int, w2: int, n2: int) -> float:
    """H1: taxa 1 > taxa 2 (z de duas proporções, unilateral)."""
    p1, p2 = w1 / n1, w2 / n2
    p = (w1 + w2) / (n1 + n2)
    erro = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if erro == 0:
        return 1.0
    return float(norm.sf((p1 - p2) / erro))
