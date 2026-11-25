"""Registro de modelos em arquivos (ADR-09): versões, métricas e o campeão de cada combinação.

Promoção só com aprovação nos critérios de validação e taxa fora da amostra acima da do
campeão atual (champion/challenger).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib


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

    def promover(self, ativo: str, expiracao: str, versao: str) -> None:
        m = self._metricas(ativo, expiracao, versao)
        if not m.get("aprovada"):
            raise ErroPromocao(f"{versao} não passou nos critérios de validação")
        atual = self.campeao(ativo, expiracao)
        if atual is not None and m["taxa"] <= atual["taxa"]:
            raise ErroPromocao(
                f"{versao} ({m['taxa']:.4f}) não supera o campeão {atual['versao']} "
                f"({atual['taxa']:.4f})"
            )
        (self._dir(ativo, expiracao) / "campeao.json").write_text(
            json.dumps({"versao": versao, "taxa": m["taxa"]})
        )
