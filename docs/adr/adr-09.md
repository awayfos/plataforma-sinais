# ADR-09: Registro de modelos próprio (tabela `model_versions` + artefatos em vo

- **Status:** aceita (design aprovado em 2026-11-25)
- **Fonte:** design §7.2

## Decisão

**Registro de modelos próprio** (tabela `model_versions` + artefatos em volume ou armazenamento S3-compatível).

## Motivo

Poucos modelos, controle de champion/challenger no próprio banco.

## Alternativas descartadas

MLflow (mais um serviço, reavaliar se o volume crescer).
