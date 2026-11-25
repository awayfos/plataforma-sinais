# ADR-07: pandas/NumPy e indicadores próprios

- **Status:** aceita (design aprovado em 2026-11-25)
- **Fonte:** design §7.2

## Decisão

**pandas/NumPy** para dados. Indicadores implementados na nossa biblioteca e testados contra uma referência (TA-Lib ou pandas-ta) só nos testes.

## Motivo

Controle total sobre o "fechado em t" e sobre os parâmetros. Sem dependência de produção de biblioteca de terceiros.

## Alternativas descartadas

Usar TA-Lib em produção (dependência C, menos controle do alinhamento).
