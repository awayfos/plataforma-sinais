# Plataforma de Inteligência de Mercado

Análise de mercado e sinais validados estatisticamente para opções binárias (V1: BTCUSDT e ETHUSDT).

- Design: `docs/superpowers/specs/2026-11-25-plataforma-sinais-design.md`
- Progresso: `docs/PROGRESSO.md`
- **Rodar no seu computador (passo a passo): `docs/COMO-RODAR-LOCAL.md`**
- Contrato da API: `docs/api/contrato-v1.md`

## Backend

```bash
cd backend
uv sync              # instala dependências (requer rede)
uv run pytest        # testes
uv run mypy          # tipos
uv run ruff check    # lint
```

## Rodar localmente (resumo)

```bash
infra/dev.sh subir                                  # backend completo no Docker (cria o .env se faltar)
infra/dev.sh admin voce@exemplo.com "Seu Nome"      # admin com 2FA (mostra a URI do autenticador)
cd frontend && npm ci && npm run dev                # site
```

Abra **http://localhost:3000** (use `localhost`, não `127.0.0.1`). Detalhes, cliente/plano, Windows e problemas comuns:
`docs/COMO-RODAR-LOCAL.md`.

## Frontend

`frontend/README.md` (Next.js 16, testes com Vitest e Playwright).
