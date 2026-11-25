# ADR-10: Explicações por templates determinísticos na V1

- **Status:** aceita (design aprovado em 2026-11-25)
- **Fonte:** design §7.2

## Decisão

**Explicação dos sinais por templates determinísticos na V1**, a partir dos dados estruturados do motor. IA generativa opcional depois, recebendo só JSON estruturado, com validação automática de que todo número do texto existe no JSON.

## Motivo

Garante que a explicação não invente dados. Custo zero na V1.

## Alternativas descartadas

LLM livre (risco de inventar números).
