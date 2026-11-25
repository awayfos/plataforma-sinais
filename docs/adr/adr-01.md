# ADR-01: Monólito modular em Python com vários processos (coletores, análise, s

- **Status:** aceita (design aprovado em 2026-11-25)
- **Fonte:** design §7.2

## Decisão

**Monólito modular em Python** com vários processos (coletores, análise, sinais, liquidador, API) que compartilham um único pacote `sinais`.

## Motivo

Um só código para backtest e produção. Simples de operar e aguenta milhares de usuários. Pode ser dividido depois.

## Alternativas descartadas

Microsserviços (custo operacional sem ganho agora).
