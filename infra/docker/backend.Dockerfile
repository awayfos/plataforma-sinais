# syntax=docker/dockerfile:1
FROM python:3.13-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app

FROM base AS deps
COPY pyproject.toml alembic.ini ./
COPY src ./src
COPY migracoes ./migracoes
# Trocar por `uv sync --frozen --no-dev` assim que uv.lock for gerado (requer rede).
RUN uv sync --no-dev

FROM base AS runtime
RUN useradd --create-home --uid 10001 sinais
COPY --from=deps /app /app
ENV PATH="/app/.venv/bin:$PATH"
USER sinais
