# ADR-05: Redis para Redis Streams (eventos entre processos, com grupos de consu

- **Status:** aceita (design aprovado em 2026-11-25)
- **Fonte:** design §7.2

## Decisão

**Redis** para Redis Streams (eventos entre processos, com grupos de consumidores), cache, rate limiting e fan-out para WebSockets.

## Motivo

Já está na pilha pedida. Streams dão entrega pelo menos uma vez com reconhecimento.

## Alternativas descartadas

Kafka (pesado), RabbitMQ (mais uma peça).
