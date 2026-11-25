# ADR-14: Logs JSON, métricas Prometheus e rastreamento de erros

- **Status:** aceita (design aprovado em 2026-11-25)
- **Fonte:** design §7.2

## Decisão

**Logs estruturados em JSON** (structlog), métricas Prometheus, painéis Grafana, erros no Sentry (ou similar autohospedado).

**Ajuste na implementação (Fase 2, 2026-11-25):** os logs JSON usam `logging` da biblioteca padrão com um formatador próprio (`sinais.logs`), em vez de structlog. Isso evita uma dependência e entrega o mesmo formato de uma linha JSON por evento. Se o volume de campos contextuais crescer, a troca por structlog fica restrita a `sinais.logs`.

## Motivo

Requisito de monitoramento. Diagnóstico de qualidade de dados e latência.

## Alternativas descartadas

—
