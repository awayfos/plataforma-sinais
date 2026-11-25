# ADR-12: Sessões no servidor, Argon2id e 2FA para admin

- **Status:** aceita (design aprovado em 2026-11-25)
- **Fonte:** design §7.2

## Decisão

**Sessões no servidor** (cookie httpOnly, Secure, SameSite=Lax, id opaco no Redis/PostgreSQL), senha com **Argon2id**, 2FA (TOTP) obrigatório para admin. Assinatura verificada no servidor em toda requisição REST e em toda conexão e inscrição WebSocket.

## Motivo

Revogação imediata (bloqueio e vencimento valem na hora), sem JWT de longa duração no navegador.

## Alternativas descartadas

JWT puro (revogação difícil).
