# PROGRESSO — Plataforma de Inteligência para Opções Binárias

Documento central para retomar o desenvolvimento sem perder decisões. Atualizado ao fim de cada fase e a cada decisão importante.

## Estado atual

- **Fase atual:** 2 — Estrutura inicial
- **Status:** implementada na branch `fase-02-estrutura-inicial`, aguardando aprovação do cliente
- **Próximo passo:** aprovação da Fase 2 → plano da Fase 3 (dados de mercado da Binance)

## Fases

| Fase | Nome | Status | Aprovada em |
|---|---|---|---|
| 1 | Planejamento e arquitetura | Aprovada | 2026-11-25 |
| 2 | Estrutura inicial | Em revisão (`docs/fases/fase-02.md`) | — |
| 3 | Dados de mercado | Não iniciada | — |
| 4 | Motores de análise | Não iniciada | — |
| 5 | Backtesting e validação | Não iniciada | — |
| 6 | Modelos e calibração (relatório de decisão) | Não iniciada | — |
| 7 | Motor de sinais ao vivo (início do teste de 60 a 90 dias) | Não iniciada | — |
| 8 | Contas e autenticação | Não iniciada | — |
| 9 | Plataforma web | Não iniciada | — |
| 10 | Administração | Não iniciada | — |
| 11 | Segurança, carga, legal e lançamento V1 | Não iniciada | — |
| 12 | V1.1 | Não iniciada | — |

## Decisões registradas

| Data | Decisão | Quem | Onde |
|---|---|---|---|
| 2026-11-25 | Produto centrado na análise; sinais só onde validados; sem promessa de retorno | Cliente | Design §1, §5 |
| 2026-11-25 | Caminho de construção A: pesquisa primeiro, monólito modular | Cliente | Design §4 |
| 2026-11-25 | Sem ativos OTC; mercados reais nos horários reais; BTC e ETH nos fins de semana | Cliente | Design §2, §5 |
| 2026-11-25 | Exnova como primeira corretora; Binance e provedores externos como referência | Cliente | Design §5 |
| 2026-11-25 | Liquidação automática, sem input do usuário | Cliente | Design §12 |
| 2026-11-25 | Nove melhorias aceitas (validação primeiro, baselines, teste ao vivo, código único, desligamento automático, detectores por evidência, gestão de risco, parte legal, monólito) | Cliente | Design §5 |
| 2026-11-25 | Pilha técnica e ADR-01 a ADR-15 | Cliente aprovou o design | `docs/adr/` |

## Documentos

- Design da Fase 1: `docs/superpowers/specs/2026-11-25-plataforma-sinais-design.md`
- Plano da Fase 2: `docs/superpowers/plans/2026-11-25-fase-02-estrutura-inicial.md`
- Registro da Fase 2: `docs/fases/fase-02.md`

## Pendências

- Rede para instalar pacotes: liberar para rodar ruff, gerar `uv.lock` e subir o Docker Compose.

- Parecer jurídico sobre CVM e defesa do consumidor (portão da Fase 11).
- Payout e regra de empate de cada ativo na Exnova (cadastro no admin).
- Grade de vencimento e corte de compra de 5 min, 30 min e 1 h na Exnova (confirmar antes da Fase 5). Já confirmados: 1 min (corte com 30 s restantes) e 15 min (corte 5 min antes).
- Orçamento de dados: zero no início. V1 só com BTC e ETH. Forex, metais e ações quando houver verba.
- Mercado de venda e país da empresa (escopo do parecer jurídico, Fase 6).
