# ADR-13: Tudo em UTC com milissegundos

- **Status:** aceita (design aprovado em 2026-11-25)
- **Fonte:** design §7.2

## Decisão

**Tudo em UTC com milissegundos.** O horário do servidor é sincronizado por NTP (chrony) e o desvio em relação à Binance é medido por `GET /api/v3/time`.

## Motivo

Liquidação e janela de entrada dependem de segundos.

## Alternativas descartadas

—
