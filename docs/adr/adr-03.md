# ADR-03: FastAPI (série 0

- **Status:** aceita (design aprovado em 2026-11-25)
- **Fonte:** design §7.2

## Decisão

**FastAPI** (série 0.14x, versão fixada com `==` por ser 0.x) + Pydantic v2 + Uvicorn.

## Motivo

Assíncrono, tipado, WebSocket nativo, documentação OpenAPI.

## Alternativas descartadas

Django (mais pesado para API em tempo real).
