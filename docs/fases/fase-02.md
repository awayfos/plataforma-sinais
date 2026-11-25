# Fase 2 — Estrutura inicial

- **Status:** em revisão (aguardando aprovação do cliente)
- **Plano:** `docs/superpowers/plans/2026-11-25-fase-02-estrutura-inicial.md`
- **Branch:** `fase-02-estrutura-inicial`

## 1. Objetivo

Criar a base do projeto: o monorepo, o núcleo de domínio sem I/O (`sinais.core`), os logs estruturados, a infraestrutura Docker Compose e o pipeline de CI.

## 2. Entregue

| Módulo | Conteúdo |
|---|---|
| `sinais.core.tempo` | Instantes em ms UTC, validação, conversão de e para `datetime` e ISO 8601, relógio do sistema e relógio fixo para testes |
| `sinais.core.dominio` | Tempos gráficos (1m a 1w), alinhamento de candles (semana começa segunda 00:00 UTC), expirações da V1, direção, classe de ativo, `Ativo`, ativos da V1 (BTCUSDT e ETHUSDT) |
| `sinais.core.calendario` | Cripto 24/7. Forex e metais de domingo 17:00 a sexta 17:00 em Nova York, com horário de verão. Ações ficam para a V1.1. |
| `sinais.core.config` | Configuração por variáveis `SINAIS_*`, segredos ocultos, erros que nomeiam a variável sem expor valores |
| `sinais.logs` | Uma linha JSON por evento, exceção num campo único, configuração idempotente |
| `infra/` | Compose com PostgreSQL 18 + TimescaleDB, Redis 8 e backend. Dockerfile com usuário não root. |
| `.github/workflows/ci.yml` | ruff, mypy strict, pytest com cobertura mínima de 90% e validação do Compose |
| `docs/adr/` | ADR-01 a ADR-15 |

## 3. Testes (saída real, 2026-11-25)

```
$ cd backend && python3 -m pytest -q
53 passed in 0.12s
$ python3 -m mypy        # strict
Success: no issues found in 16 source files
$ docker compose -f infra/docker-compose.yml --env-file .env.example config -q
(exit 0)
```

Cobertura de linhas medida com o módulo `trace` da stdlib (o `pytest-cov` não pôde ser instalado): `sinais.core` e `sinais.logs` com 100%.

## 4. Auditoria: o que foi verificado e o que não foi

| Item | Verificado aqui? | Observação |
|---|---|---|
| Testes unitários e mypy strict | Sim | — |
| Validação do Compose | Sim | `config -q` e falha clara quando falta variável |
| `docker compose up` (imagens, healthchecks) | **Não** | Sem daemon Docker e sem rede neste ambiente |
| ruff (lint e formatação) | **Não** | Pacote não instalável sem rede. Roda no primeiro CI. |
| `uv sync` e `uv.lock` | **Não** | Requer rede. O Dockerfile usa `uv sync` sem `--frozen` até o lock existir. |
| CI no GitHub | **Não** | Não há repositório remoto. |

## 5. Critérios de aprovação (design §17)

- [x] Testes de `core` passando
- [ ] CI verde: depende do primeiro push para um repositório remoto
- [ ] Ambiente sobe com um comando: depende de executar `docker compose up` numa máquina com Docker e rede
