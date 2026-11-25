# ADR-04: PostgreSQL 18 + TimescaleDB 2

- **Status:** aceita (design aprovado em 2026-11-25)
- **Fonte:** design §7.2

## Decisão

**PostgreSQL 18 + TimescaleDB 2.x** (≥ 2.29, que suporta PG 16 a 18).

## Motivo

Séries temporais com compressão e particionamento automático, mantendo SQL e transações no mesmo banco dos usuários.

## Alternativas descartadas

Banco de séries separado (InfluxDB, ClickHouse), que traz mais uma peça.
