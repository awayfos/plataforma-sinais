# Fase 3 — Dados de mercado da Binance

- **Status:** concluída na branch `fase-03-dados-binance` (CI verde), aguardando a revisão final
- **Plano:** `docs/superpowers/plans/2026-11-25-fase-03-dados-binance.md`

## 1. Objetivo

Coletar candles fechados de 1 s e 1 min de BTCUSDT e ETHUSDT (histórico por REST e tempo real por WebSocket), conferir a qualidade, agregar os tempos gráficos maiores, gravar no TimescaleDB e publicar `candle.fechado` no Redis.

## 2. Entregue

| Módulo | Conteúdo |
|---|---|
| `dados.modelos` | `Candle` com preços em `Decimal` e validação (máxima/mínima, alinhamento, volumes) |
| `dados.provedores.binance.parsing` | Linhas do REST e mensagens do WebSocket. Candles em formação são marcados e nunca tratados como fechados. |
| `dados.provedores.binance.rest` | Cliente REST: 429 respeita `Retry-After`, 418 interrompe, 5xx e falha de rede com backoff (até 5 tentativas) |
| `dados.provedores.binance.streams` | Streams combinados, reconexão com backoff, renovação aos 23 h 50 min e preenchimento da lacuna a cada reconexão |
| `dados.qualidade` | Lacunas, duplicados e fora de ordem |
| `dados.agregacao` | 3m a 1w a partir de 1m, só com blocos completos |
| `dados.backfill` | Histórico em janelas de 1000, com as lacunas da fonte registradas |
| `dados.conferencia` | Compara a agregação local com os klines oficiais |
| `persistencia` | Tabelas, migração Alembic (hypertables), repositório PostgreSQL e dublê em memória com o mesmo contrato |
| `eventos` | Contrato `candle.fechado` e publicador no Redis Streams |
| `processos.coletor_binance` | Processo completo |
| `infra` | Compose com `migracoes` e `coletor`. `fumaca.sh` sobe tudo e confere dados reais. |

## 3. Testes (saída real do CI, 2026-11-25)

| Job | Resultado |
|---|---|
| backend | ruff ok, mypy strict ok, **135 testes passando**, cobertura de `core`, `logs` e `dados` em **97%** |
| integracao | **6 testes** contra TimescaleDB real: contrato do repositório e hypertables criadas |
| infra | Compose válido |
| fumaca | Ambiente completo com **dados reais da Binance**: 2.880 candles de 1m, 172.808 de 1s, eventos ao vivo publicados. Conferência: BTCUSDT e ETHUSDT, 5m (72 candles) e 1h (6 candles), **0 divergências** em relação aos klines oficiais. |

## 4. Auditoria

| Critério do design (§17) | Situação |
|---|---|
| Histórico sem lacunas não explicadas | Toda lacuna da fonte vira registro em `eventos_qualidade`. Nenhuma lacuna nas execuções do CI. |
| Agregação idêntica aos klines oficiais | **Comprovado** no CI (0 divergências) |
| 72 h ao vivo sem perda | **Não verificado**: exige o coletor rodando 3 dias num servidor |
| Relatório de qualidade | Eventos de qualidade gravados no banco. O relatório visual vem com o painel admin. |
| Ambiente sobe com um comando (pendência da Fase 2) | **Comprovado** no CI pelo job `fumaca` |

Limitações conhecidas:
- O histórico longo de 1 s (2 anos) não vem pelo REST. Ele virá dos arquivos mensais da Binance, na Fase 5.
- Os runners do GitHub usam o endpoint só de dados de mercado (`data-api.binance.vision`). Em produção, o padrão é `api.binance.com` e pode ser trocado por variável.
