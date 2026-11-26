# PROGRESSO — Plataforma de Inteligência para Opções Binárias

Documento central para retomar o desenvolvimento sem perder decisões. Atualizado ao fim de cada fase e a cada decisão importante.

## Estado atual

- **Fases atuais:** plataforma (Fases 7 parcial, 8, 9 e 10) integrada em `main`; **Fase 6c — motor de situações** em andamento (branch `fase-06c-situacoes`). Sinais continuam em **AGUARDAR** em todas as expirações: nenhum modelo aprovado.
- **Fase 6 (modelo v1):** 53–55,5% fora da amostra (estratégias simples ~50%). Com o payout real da Exnova (86–89%), só BTC 1m passou no walk-forward e foi **reprovado na validação realista com 1 s** (54,10%, Wilson 52,98% < equilíbrio 53,76%; 62% das operações apertadas) (`docs/fases/fase-06.md`).
- **Fase 6b (modelo v2: rótulos de 1 s, microestrutura fs-2, filtro de apertados): nenhuma combinação aprovada** (`docs/fases/fase-06b-modelo-v2.md`, `docs/laboratorio/2026-11-26-modelo-v2-payout-86.md`). Ficou **pré-registrada** uma rodada confirmatória só com meses novos (holdout 2026-11, 2026-12 e 2027-01; entrada + 2..+10 s, tolerância de 0,5 × ATR, payout 0,86), que só pode rodar depois da publicação de 2027-01 na Binance (**a partir de 2027-02**). A **emenda A** acrescentou uma segunda família declarada, BTC/ETH × **15m e 30m**, com a mesma configuração e Benjamini-Hochberg próprio. É a única rodada que pode ligar uma combinação.
- **Fase 6c (motor de situações):** em andamento em `fase-06c-situacoes` (camadas A/B, pré-registro e confirmação mensal em meses novos); ainda sem resultado de aprovação.
- **Gráfico tick a tick provado igual à Binance:** o job `ticks` do CI grava aggTrades reais por 3 minutos e compara cada 1m (e o 5m) montado negócio a negócio com os klines oficiais, com igualdade exata de `Decimal` (`docs/fases/fase-07-08-10-backend.md`).
- **Payout da Exnova (informado pelo cliente):** 86% a 89%.
- **Primeiro resultado real:** estratégias simples ~50% de acerto contra 54,05% de equilíbrio (payout 0,85 hipotético) → valor esperado ≈ −7% por operação (`docs/laboratorio/2026-11-25-baselines.md`). Com preços de 1 s: até 51,1%, e 41% das operações de 1 min do BTC terminam "apertadas" (`docs/laboratorio/2026-11-25-baselines-1s.md`)
- **Rodar localmente:** `docs/COMO-RODAR-LOCAL.md`.
- **Repositório:** https://github.com/awayfos/plataforma-sinais (privado)
- **Modo de trabalho:** o cliente pediu em 2026-11-25 para seguir sem pausa de aprovação entre fases. Os portões de decisão (modelos, jurídico, lançamento) continuam com ele.

## Fases

| Fase | Nome | Status | Aprovada em |
|---|---|---|---|
| 1 | Planejamento e arquitetura | Aprovada | 2026-11-25 |
| 2 | Estrutura inicial | Concluída (`docs/fases/fase-02.md`) | 2026-11-25 |
| 3 | Dados de mercado | Concluída (`docs/fases/fase-03.md`) | 2026-11-25 |
| 4 | Motores de análise | Concluída (`docs/fases/fase-04.md`) | 2026-11-25 |
| 5 | Backtesting e validação | Concluída (`docs/fases/fase-05.md`) | 2026-11-25 |
| 6 | Modelos e calibração (relatório de decisão) | Concluída — nenhuma combinação validada (`docs/fases/fase-06.md`) | 2026-11-25 |
| 6b | Modelo v2 (1 s, microestrutura, filtro) | Concluída — nenhuma aprovada; confirmatória pré-registrada para meses novos a partir de 2027-02, com emenda 15m/30m (`docs/fases/fase-06b-modelo-v2.md`) | 2026-11-26 |
| 6c | Motor de situações | Em andamento (branch `fase-06c-situacoes`) | — |
| 7 | Motor de sinais ao vivo (início do teste de 60 a 90 dias) | Parcial: **análise ao vivo** pronta (motor de análise, velas tick a tick 1m–1w, WebSocket); **motor de sinais, liquidador e monitor pendentes de um campeão aprovado** (`docs/fases/fase-07-08-10-backend.md`) | — |
| 8 | Contas e autenticação | Concluída (PR #14; correções da revisão de integração em `integracao-correcoes`) | — |
| 9 | Plataforma web | Concluída (PR #13), aguardando revisão visual do cliente (`docs/fases/fase-09-frontend.md`) | — |
| 10 | Administração | Concluída (PR #14 + botão "Encerrar assinatura") | — |
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
- Plano e registro da Fase 3: `docs/superpowers/plans/2026-11-25-fase-03-dados-binance.md`, `docs/fases/fase-03.md`
- Plataforma: `docs/fases/fase-07-08-10-backend.md` (backend), `docs/fases/fase-09-frontend.md` (frontend), contrato `docs/api/contrato-v1.md`
- Como rodar localmente: `docs/COMO-RODAR-LOCAL.md`

## Pendências

- `uv.lock`: gerar com rede para builds reproduzíveis.
- Teste de 72 h ao vivo do coletor: exige servidor.
- Rodada confirmatória da Fase 6b (com a emenda 15m/30m): a partir de 2027-02, depois da publicação de 2027-01.
- Itens menores adiados da revisão de integração (M4, M5, M6, M7, M12): `docs/fases/fase-07-08-10-backend.md`, seção "Revisão de integração".
  - M4: cada WebSocket revalida a sessão a cada 5 s (~3 consultas por conexão) e mantém a sessão "ativa" enquanto a aba estiver aberta.
  - M5: corrida na subida da API entre a carga do banco e o primeiro 1m oficial (se corrige na recarga seguinte, em até 1 min).
  - M6: o conjunto de ids de negócios por minuto não tem limite se o coletor travar.
  - M7: segredos TOTP gravados antes do formato `k1:` + AAD não abrem (só existiram em dev/CI; refazer com `criar_admin`).
  - M12: `/api/candles` de 1d/1w agrega a partir do 1m a cada carga (lento com 730 dias de histórico); candidato a agregado contínuo do TimescaleDB.

- Parecer jurídico sobre CVM e defesa do consumidor (portão da Fase 11).
- Regra de empate confirmada pela pesquisa (devolve o valor); payout informado: 86% a 89%.
- Grade de vencimento e corte de compra de 5 min, 30 min e 1 h na Exnova (confirmar antes da Fase 5). Já confirmados: 1 min (corte com 30 s restantes) e 15 min (corte 5 min antes).
- Orçamento de dados: zero no início. V1 só com BTC e ETH. Forex, metais e ações quando houver verba.
- Mercado de venda e país da empresa (escopo do parecer jurídico, Fase 6).
