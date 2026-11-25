# ADR-08: LightGBM como primeiro modelo, com calibração isotônica ou de Platt em

- **Status:** aceita (design aprovado em 2026-11-25)
- **Fonte:** design §7.2

## Decisão

**LightGBM** como primeiro modelo, com calibração isotônica ou de Platt em fatia separada. Redes neurais só como desafiantes.

## Motivo

Bom com dados tabulares, menos sobreajuste e explicável (contribuição de cada feature via SHAP).

## Alternativas descartadas

Deep learning primeiro (mais dados, mais sobreajuste, menos explicável).
