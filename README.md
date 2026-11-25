# Plataforma de Inteligência de Mercado

Análise de mercado e sinais validados estatisticamente para opções binárias (V1: BTCUSDT e ETHUSDT).

- Design: `docs/superpowers/specs/2026-11-25-plataforma-sinais-design.md`
- Progresso: `docs/PROGRESSO.md`

## Backend

```bash
cd backend
uv sync              # instala dependências (requer rede)
uv run pytest        # testes
uv run mypy          # tipos
uv run ruff check    # lint
```

## Infraestrutura local

```bash
cp .env.example .env
docker compose -f infra/docker-compose.yml --env-file .env up -d
```
