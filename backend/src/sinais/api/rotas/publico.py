"""``/api/publico``: sem sessão. Só estatísticas agregadas, nunca sinais individuais."""

from __future__ import annotations

from fastapi import APIRouter

from sinais.api import esquemas as e

rotas = APIRouter(prefix="/api/publico", tags=["público"])


@rotas.get("/estatisticas", response_model=list[e.EstatisticaPublica])
async def estatisticas() -> list[e.EstatisticaPublica]:
    """Por ativo e expiração (n, taxa, período). Vazio até existirem sinais liquidados."""
    return []
