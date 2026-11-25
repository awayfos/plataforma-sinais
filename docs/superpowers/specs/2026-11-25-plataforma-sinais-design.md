# Plataforma de Inteligência para Opções Binárias — Design da Fase 1

- **Data:** 2026-11-25
- **Status:** rascunho para aprovação (Fase 1, planejamento e arquitetura)
- **Base:** documento de requisitos original do cliente + decisões tomadas na conversa de 24 e 25/11/2026
- **Idioma do produto:** português do Brasil

> Convenção deste documento: **[Cliente]** marca uma decisão tomada pelo dono do produto. **[Arquiteto]** marca uma decisão técnica minha, que pode ser revista. Sem marcação = requisito do documento original.

---

## 1. Intenção e porquê

O cliente quer um produto comercial, vendido por assinatura, que mostre ao usuário a direção do mercado e aquilo que ele não enxerga sozinho, para operar opções binárias com mais acerto. **[Cliente]** O produto não garante retorno. Ele entrega sinais de alta qualidade e análises sérias, e aprende com cada sinal para melhorar com o tempo.

"Melhor sinal" neste projeto tem uma definição operacional: **um sinal só existe se a combinação ativo × expiração × condição de mercado tiver vantagem comprovada fora da amostra, acima do ponto de equilíbrio do payout.** Fora disso, o produto mostra AGUARDAR e explica por quê.

O usuário de referência opera na corretora **Exnova**, cujos gráficos espelham preços de mercado reais (por exemplo, o BTC/USDT da Binance Spot). **[Cliente]** Ele opera só mercados reais, nos horários reais de cada ativo. Com as bolsas fechadas, opera só BTC e ETH.

## 2. Objetivos, não objetivos e antiobjetivos

### Objetivos
1. Análise completa e sempre visível por ativo: tendência por tempo gráfico, regiões difíceis de romper, desaceleração, impulso, volume, liquidez e estrutura.
2. Sinais COMPRA, VENDA ou AGUARDAR **por expiração**, cada um com probabilidade calibrada e tamanho da amostra (n).
3. Validação estatística rigorosa antes de qualquer sinal chegar ao cliente: walk-forward, fora da amostra, sem look-ahead.
4. Liquidação automática de todos os sinais e histórico público, incluindo as derrotas.
5. Aprendizado contínuo com trava: um novo modelo só substitui o atual se for melhor em dados que nunca viu.
6. Fácil para iniciantes e completo para experientes (modos Essencial e Avançado).
7. Plataforma SaaS com login, assinatura com vencimento, painel admin e, na V1.1, área de cursos.

### Não objetivos (fora do escopo)
- **Ativos OTC.** O preço é interno da corretora e nenhuma fonte externa o reproduz. **[Cliente + Arquiteto]**
- **Execução automática de ordens** em qualquer corretora (requisito original).
- Integração direta com a Exnova (não há API pública conhecida).
- Vídeos nas aulas (V1.1 usa texto, imagens geradas e testes).
- Notificações fora da plataforma (celular, Telegram) na V1. Ficam para a V1.1.

### Antiobjetivos (resultados que tornam o projeto um fracasso mesmo que "funcione")
- Mostrar uma probabilidade que não foi validada, ou "70%" que na prática acerta 55%.
- Emitir sinais só para o sistema parecer ativo.
- Um backtest bonito que não se repete ao vivo (look-ahead, vazamento de dados, entradas impossíveis).
- Apresentar dado ilustrativo ou simulado como se fosse real.
- Usuário de um plano acessando dados de outro usuário, ou assinatura validada só no navegador.

## 3. Restrições

| Restrição | Consequência no design |
|---|---|
| **Regulatória (Brasil).** A CVM trata ofertas de opções binárias a residentes no Brasil como irregulares e emitiu stop orders contra corretoras. | Parecer jurídico obrigatório antes de vender (portão do lançamento). Termos de uso, aviso de risco e LGPD desde a V1. Nenhum link de afiliado ou incentivo a operar. |
| **Payout abaixo de 100%.** Com payout `r`, o ponto de equilíbrio é `p* = 1 / (1 + r)`: 52,6% a 90%, 54,1% a 85%, 55,6% a 80%. | O critério de validação usa `p*` de cada ativo na corretora, cadastrado no admin. |
| **Regras da plataforma Quadcode (Exnova, IQ Option).** Empate (fechamento igual à abertura) devolve o valor investido. O payout é definido por ativo, chega a no máximo 95% e aparece no painel da corretora. A plataforma também oferece Opções Digitais e Blitz (5 a 30 s), que funcionam de outro jeito. | TIE conta como devolução nas estatísticas: não é vitória nem derrota, mas entra no cálculo de valor esperado como resultado zero. Escopo restrito às Opções Binárias clássicas. Digitais e Blitz ficam fora. |
| **Preço da Exnova ≠ preço de referência.** São próximos, mas não idênticos, e a Exnova não tem API. | Liquidação pela fonte de referência. Resultados "apertados" são marcados e reportados à parte (seção 11). |
| **Binance WebSocket.** Uma conexão aceita no máximo 1024 streams, é derrubada após 24 h, aceita 5 mensagens recebidas por segundo, limite de 300 conexões a cada 5 min por IP, ping a cada 20 s. | Uma conexão de streams combinados por processo coletor, renovação proativa antes de 24 h, controle de taxa nas inscrições. |
| **Bloqueio geográfico da Binance.** A API recusa acessos de algumas jurisdições (por exemplo, servidores nos EUA). | Hospedar a coleta numa região permitida. Verificar na Fase 3. |
| **Dados de forex e metais.** Planos gratuitos costumam ter atraso, limite de requisições ou não ter streaming. | **[Cliente]** Sem orçamento no início: a V1 fica só com cripto (Binance, gratuita). Forex e metais entram quando houver verba, com o provedor escolhido por avaliação nesse momento. |
| **Horários de mercado.** Ações só no pregão dos EUA. Forex e metais de domingo à noite até sexta (UTC). Cripto 24/7. Horário de verão dos EUA muda os horários em Brasília. | Calendário por ativo, tudo armazenado em UTC, conversão só na tela. Fora do horário, o ativo fica "fechado", sem análise nem sinal. |
| **Janela de entrada curta.** Em 1 min o usuário tem segundos para entrar na Exnova. | V1 com painel web aberto ao lado da Exnova, alerta sonoro e visual, latência medida de ponta a ponta. |

## 4. Abordagens consideradas

| | A) Pesquisa primeiro, monólito modular | B) Laboratório e plataforma em paralelo | C) Microsserviços com fila de eventos desde o início |
|---|---|---|---|
| Ideia | Dados, motores, backtest e modelos primeiro. Depois o motor ao vivo. Depois a plataforma web. | Interface e pesquisa ao mesmo tempo. | Serviços separados com Kafka ou similar. |
| A favor | Responde primeiro se existe vantagem, e onde, com o menor custo. | Interface visível mais cedo. | Escala muito grande. |
| Contra | Nos primeiros blocos só há relatórios. | Pode polir uma vitrine para sinais sem valor. Retrabalho se a validação mudar o sinal. | Peso operacional enorme, atrasa tudo e não melhora os sinais. |
| **Escolha** | **[Cliente] escolhida** | | |

## 5. Decisões do cliente registradas na conversa

1. Caminho B do produto: a análise forte é o centro, os sinais aparecem só onde houver validação e não há promessa de retorno.
2. Aprender com cada sinal, com trava de champion/challenger e teste fora da amostra.
3. Ativos-alvo: BTC, ETH, ouro, prata, Apple, Nvidia, Coca-Cola e pares de forex. Só mercados reais, sem OTC.
4. Corretora inicial: Exnova. Fonte de referência: Binance para cripto e provedores externos para os demais.
5. Liquidação 100% automática, sem o usuário informar resultados.
6. Janela de entrada (tempo e preço) explícita em cada sinal, com aviso de que operações curtas exigem entrada bem posicionada.
7. Modos Essencial e Avançado. Ícone "aprenda" em cada termo técnico.
8. Cursos (V1.1): texto escrito do zero a partir de pesquisa, com fontes citadas. Imagens geradas pelo motor de gráficos da plataforma, num padrão visual único. Exemplos reais identificados e desenhos didáticos com o selo "ilustrativo". Revisão do cliente antes de publicar. Teste no fim de cada aula.
9. Tela do ativo com uma linha por expiração (1, 5, 15 e 30 min e 1 h): direção, probabilidade calibrada e n.
10. Todas as nove melhorias propostas foram aceitas: validar antes de construir, comparação com estratégias simples, 60 a 90 dias de teste ao vivo antes de cobrar, código único para backtest e produção, desligamento automático, poucos detectores escolhidos por evidência, gestão de risco no produto, parte legal desde o início, monólito modular.

## 6. Escopo por versão

| Item | V1 (lançamento pago) | V1.1 | Depois |
|---|---|---|---|
| Ativos | **[Cliente]** BTC e ETH (dados gratuitos da Binance, sem orçamento de dados no início; o cliente opera só Bitcoin hoje) | Ouro, prata, forex e ações, quando houver orçamento para dados | Novos ativos por configuração |
| Expirações | 1, 5, 15 e 30 min e 1 h | 2, 3 e 10 min (requisito original) | — |
| Tempos gráficos | 1m, 3m, 5m, 15m, 30m, 1h, 4h, 1d, 1w | Períodos em segundos (cripto, via klines de 1 s ou trades) | — |
| Análise | Biblioteca completa disponível. No motor de decisão, só os detectores aprovados por evidência. | Novos detectores medidos um a um | — |
| Sinais | Só nas combinações que passaram na validação | — | — |
| Gráfico | Velas, volume, zoom, indicadores configuráveis, linhas, zonas, layouts salvos | Mais ferramentas de desenho | — |
| Usuários | Login, perfil, troca de senha, plano, vencimento, histórico | — | Gateway de pagamento |
| Admin | Usuários, planos, assinaturas, permissões, acessos, travas de sinal, payout por ativo | Editor de aulas | — |
| Gestão de risco | Calculadora de entrada e aviso de muitos sinais seguidos no dia | Stop diário com registro opcional de resultados | — |
| Cursos | — | Área de cursos completa | Vídeo |
| Notificações | Alerta sonoro e visual no painel | Celular e Telegram | — |
| Corretoras | Exnova (cadastro manual de regras e payout) | — | Outras corretoras por adaptador |

## 7. Arquitetura

### 7.1 Visão geral

```
            ┌──────────────────────── Fontes externas ────────────────────────┐
            │ Binance REST/WS (BTC, ETH)      Provedor forex/metais (REST/WS) │
            └───────────────┬─────────────────────────────┬───────────────────┘
                            │                             │
                  ┌─────────▼─────────┐         ┌─────────▼─────────┐
                  │ coletor-binance   │         │ coletor-forex     │   (processos separados)
                  └─────────┬─────────┘         └─────────┬─────────┘
                            └──────────┬──────────────────┘
                                       ▼
                      ┌────────────────────────────────┐
                      │ normalização + qualidade       │ → candles FECHADOS no PostgreSQL/TimescaleDB
                      │ (gaps, duplicados, relógio)    │ → evento candle.fechado no Redis Streams
                      └───────────────┬────────────────┘
                                      ▼
                      ┌────────────────────────────────┐
                      │ motor-analise                  │  biblioteca `sinais.analise` + `sinais.features`
                      │ (indicadores, estrutura, etc.) │ → snapshot de features (versionado)
                      └───────────────┬────────────────┘
                                      ▼
                      ┌────────────────────────────────┐
                      │ motor-sinais                   │  modelo campeão + calibração + filtros + trava
                      │ (por ativo × expiração)        │ → sinal (COMPRA/VENDA/AGUARDAR) gravado
                      └───────┬───────────────┬────────┘
                              │               ▼
                              │     ┌────────────────────┐
                              │     │ liquidador         │ → resultado WIN/LOSS/TIE/SEM_DADO/apertado
                              │     └─────────┬──────────┘
                              │               ▼
                              │     ┌────────────────────┐
                              │     │ monitor-desempenho │ → desliga combinação abaixo do equilíbrio
                              │     └────────────────────┘
                              ▼
                      ┌────────────────────────────────┐        ┌──────────────────────┐
                      │ api (FastAPI REST + WebSocket) │◄──────►│ frontend (Next.js)   │
                      │ autenticação, assinatura, RBAC │        │ cliente + admin      │
                      └────────────────────────────────┘        └──────────────────────┘

  laboratório (CLI, sob demanda): backtest, walk-forward, treino, calibração, relatórios → registro de modelos
```

### 7.2 Decisões técnicas (resumo de ADRs)

| # | Decisão | Por quê | Alternativas descartadas |
|---|---|---|---|
| ADR-01 | **Monólito modular em Python** com vários processos (coletores, análise, sinais, liquidador, API) que compartilham um único pacote `sinais`. | Um só código para backtest e produção. Simples de operar e aguenta milhares de usuários. Pode ser dividido depois. | Microsserviços (custo operacional sem ganho agora). |
| ADR-02 | **Python 3.13**, gerenciado com `uv`. | Maturidade do ecossistema científico. Suporte do FastAPI, pandas, LightGBM. Versão exata validada na Fase 2. | 3.14 (adotar quando todas as dependências científicas suportarem). |
| ADR-03 | **FastAPI** (série 0.14x, versão fixada com `==` por ser 0.x) + Pydantic v2 + Uvicorn. | Assíncrono, tipado, WebSocket nativo, documentação OpenAPI. | Django (mais pesado para API em tempo real). |
| ADR-04 | **PostgreSQL 18 + TimescaleDB 2.x** (≥ 2.29, que suporta PG 16 a 18). | Séries temporais com compressão e particionamento automático, mantendo SQL e transações no mesmo banco dos usuários. | Banco de séries separado (InfluxDB, ClickHouse), que traz mais uma peça. |
| ADR-05 | **Redis** para Redis Streams (eventos entre processos, com grupos de consumidores), cache, rate limiting e fan-out para WebSockets. | Já está na pilha pedida. Streams dão entrega pelo menos uma vez com reconhecimento. | Kafka (pesado), RabbitMQ (mais uma peça). |
| ADR-06 | **SQLAlchemy 2 + Alembic** para persistência e migrações. | Padrão maduro, tipado, migrações versionadas. | — |
| ADR-07 | **pandas/NumPy** para dados. Indicadores implementados na nossa biblioteca e testados contra uma referência (TA-Lib ou pandas-ta) só nos testes. | Controle total sobre o "fechado em t" e sobre os parâmetros. Sem dependência de produção de biblioteca de terceiros. | Usar TA-Lib em produção (dependência C, menos controle do alinhamento). |
| ADR-08 | **LightGBM** como primeiro modelo, com calibração isotônica ou de Platt em fatia separada. Redes neurais só como desafiantes. | Bom com dados tabulares, menos sobreajuste e explicável (contribuição de cada feature via SHAP). | Deep learning primeiro (mais dados, mais sobreajuste, menos explicável). |
| ADR-09 | **Registro de modelos próprio** (tabela `model_versions` + artefatos em volume ou armazenamento S3-compatível). | Poucos modelos, controle de champion/challenger no próprio banco. | MLflow (mais um serviço, reavaliar se o volume crescer). |
| ADR-10 | **Explicação dos sinais por templates determinísticos na V1**, a partir dos dados estruturados do motor. IA generativa opcional depois, recebendo só JSON estruturado, com validação automática de que todo número do texto existe no JSON. | Garante que a explicação não invente dados. Custo zero na V1. | LLM livre (risco de inventar números). |
| ADR-11 | **Next.js 16 (App Router) + React 19 + TypeScript + Tailwind CSS** e **TradingView Lightweight Charts 5.x**. | Pedido no requisito, versões atuais e suportadas. O Lightweight Charts 5 tem plugins (primitivas) para desenhos e zonas. | — |
| ADR-12 | **Sessões no servidor** (cookie httpOnly, Secure, SameSite=Lax, id opaco no Redis/PostgreSQL), senha com **Argon2id**, 2FA (TOTP) obrigatório para admin. Assinatura verificada no servidor em toda requisição REST e em toda conexão e inscrição WebSocket. | Revogação imediata (bloqueio e vencimento valem na hora), sem JWT de longa duração no navegador. | JWT puro (revogação difícil). |
| ADR-13 | **Tudo em UTC com milissegundos.** O horário do servidor é sincronizado por NTP (chrony) e o desvio em relação à Binance é medido por `GET /api/v3/time`. | Liquidação e janela de entrada dependem de segundos. | — |
| ADR-14 | **Logs estruturados em JSON** (structlog), métricas Prometheus, painéis Grafana, erros no Sentry (ou similar autohospedado). | Requisito de monitoramento. Diagnóstico de qualidade de dados e latência. | — |
| ADR-15 | **Docker + Docker Compose** em desenvolvimento e na primeira produção (um servidor dedicado ou VPS em região permitida pela Binance). | Requisito. Suficiente para a V1. | Kubernetes (prematuro). |

Versões exatas de todas as dependências são fixadas e verificadas na documentação oficial na Fase 2, num arquivo de lock.

## 8. Estrutura de pastas

```
plataforma-sinais/
├── docs/
│   ├── PROGRESSO.md                 # documento central de progresso (fonte da verdade)
│   ├── superpowers/specs/           # designs aprovados
│   ├── adr/                         # decisões arquiteturais, uma por arquivo
│   └── fases/                       # objetivo, plano, testes, auditoria e aprovação por fase
├── backend/
│   ├── pyproject.toml
│   ├── src/sinais/
│   │   ├── core/                    # tipos de domínio, relógio, calendário de mercado, config, erros
│   │   ├── dados/
│   │   │   ├── provedores/          # adaptadores: binance/, forex_<provedor>/  (interface MarketDataProvider)
│   │   │   ├── candles/             # agregação de tempos gráficos, validação de candles fechados
│   │   │   └── qualidade/           # gaps, duplicados, atraso, desvio de relógio
│   │   ├── analise/                 # motores independentes, só calculam, nunca decidem
│   │   │   ├── indicadores/         # RSI, MACD, EMA, SMA, VWAP, ATR, ADX, Estocástico, Bollinger, Ichimoku
│   │   │   ├── padroes_candle/      # engolfo, pin bar, doji, martelo, estrelas, marubozu, inside/outside bar
│   │   │   ├── price_action/        # tendência, lateralização, rompimento, falso rompimento, reteste, desaceleração
│   │   │   ├── estrutura/           # pivôs, HH/HL/LH/LL, BOS, CHoCH, order blocks, FVG, liquidez
│   │   │   ├── regioes/             # suporte/resistência, supply/demand, dificuldade de rompimento
│   │   │   ├── volume/              # volume relativo, expansão/contração, agressão (taker buy)
│   │   │   └── fibonacci/
│   │   ├── features/                # monta o snapshot de features a partir de `analise` (código único)
│   │   ├── modelos/                 # treino, calibração, registro, inferência, champion/challenger
│   │   ├── backtest/                # simulador, walk-forward purgado, baselines, métricas, relatórios
│   │   ├── decisao/                 # motor de sinais, filtros, trava por combinação, janela de entrada
│   │   ├── liquidacao/              # resultado no vencimento, faixa de "apertado"
│   │   ├── monitoramento/           # desempenho ao vivo, desligamento automático
│   │   ├── corretoras/              # adaptadores (interface Broker): exnova/
│   │   ├── explicacao/              # textos dos sinais por template
│   │   ├── contas/                  # usuários, planos, assinaturas, sessões, permissões, auditoria
│   │   ├── persistencia/            # modelos SQLAlchemy, repositórios, migrações Alembic
│   │   ├── eventos/                 # contratos dos eventos no Redis Streams
│   │   ├── api/                     # routers REST, gateway WebSocket, dependências de autenticação
│   │   └── processos/               # pontos de entrada: coletor_binance, coletor_forex, motor_analise,
│   │                                #   motor_sinais, liquidador, monitor, api, agendador
│   ├── laboratorio/                 # CLI de pesquisa: backtest, walk-forward, treino, relatórios
│   └── tests/
│       ├── unit/  property/  integration/  regressao_vazamento/  fixtures/
├── frontend/
│   ├── package.json
│   └── src/
│       ├── app/(publico)/  (cliente)/  (admin)/      # rotas
│       ├── components/  grafico/  sinais/  admin/
│       └── lib/ api/ ws/ tipos/                       # tipos gerados do OpenAPI
├── infra/
│   ├── docker-compose.yml  docker-compose.prod.yml
│   ├── docker/                      # Dockerfiles
│   └── observabilidade/             # Prometheus, Grafana, alertas
└── .github/workflows/               # CI: lint, tipos, testes, build
```

## 9. Módulos e responsabilidades

| Módulo | Responsabilidade | Não faz |
|---|---|---|
| `core` | Tipos de domínio (`Ativo`, `Candle`, `Expiracao`, `Direcao`), relógio injetável (para testes), calendário de mercado por ativo, configuração. | I/O |
| `dados.provedores` | Uma interface `MarketDataProvider` (histórico de candles, stream ao vivo, horário do servidor). Implementações: Binance e um provedor de forex e metais. Reconexão, backoff exponencial com jitter, renovação de conexão antes de 24 h. | Calcular indicadores |
| `dados.candles` | Emite só candles **fechados** (na Binance, `k.x == true`). Agrega tempos gráficos maiores a partir de 1m, alinhados em UTC (semana começando segunda 00:00 UTC, como na Binance). Confere a agregação contra os klines oficiais em teste. | — |
| `dados.qualidade` | Detecta gaps, duplicados, candles fora de ordem, atraso de chegada e desvio de relógio. Registra eventos e marca janelas de dados não confiáveis. A análise e os sinais param nessas janelas. | Esconder falhas |
| `analise.*` | Funções puras: entrada = série de candles fechados até `t`, saída = valores e detecções em `t`. Cada família é independente e tem parâmetros configuráveis. | Decidir operação |
| `features` | Monta o snapshot versionado (`feature_set_version`) que alimenta o modelo, **o mesmo código no laboratório e ao vivo**, incluindo contexto de outros tempos gráficos (só o último candle fechado de cada um). | — |
| `backtest` | Simulação de entradas e vencimentos, walk-forward purgado com embargo, baselines, métricas por ativo, horário e regime, relatórios. | Usar dado posterior ao instante da decisão |
| `modelos` | Treino LightGBM por expiração, calibração, registro, promoção de champion/challenger, inferência. | — |
| `decisao` | Para cada ativo × expiração no fechamento de candle: verifica mercado aberto, qualidade dos dados, trava (gate), filtros de condição desfavorável. Calcula probabilidade calibrada, define COMPRA/VENDA/AGUARDAR, janela de entrada, invalidação. Grava o sinal. | — |
| `liquidacao` | No vencimento, busca o preço de referência e grava o resultado. | — |
| `monitoramento` | Desempenho ao vivo por combinação. Desliga a combinação e alerta o admin quando ela cai abaixo do equilíbrio. | — |
| `corretoras` | Interface `Broker`: ativos, símbolo na corretora, payout, expirações, regra de empate, horários. **Perfil de plataforma "Quadcode"**: a Exnova roda na mesma plataforma white label da IQ Option (Quadcode). Segundo o cliente, a Broker10 também. As regras comuns (vencimento alinhado ao relógio com prazo de compra, empate devolve o valor, payout por ativo) ficam num perfil compartilhado, e cada marca herda o perfil e sobrescreve o que for diferente. Exnova é a primeira marca cadastrada. | Executar ordens |
| `explicacao` | Texto do sinal a partir dos dados estruturados. | Inventar números |
| `contas` | Usuários, papéis (cliente, admin), planos, assinaturas, sessões, limites, auditoria de ações do admin. | — |
| `api` | REST e WebSocket, autenticação, autorização por papel e plano, rate limiting, validação de assinatura no servidor. | Lógica de análise |

## 10. Comunicação entre módulos

- **Dentro do processo:** chamadas de função diretas para a biblioteca (`analise`, `features`, `decisao`).
- **Entre processos:** Redis Streams com grupos de consumidores. Cada evento tem id idempotente e versão de esquema. O PostgreSQL é a fonte da verdade, e um evento perdido pode ser reconstruído a partir do banco.

| Evento | Produtor | Consumidores | Conteúdo mínimo |
|---|---|---|---|
| `candle.fechado` | coletores | motor-analise, api (gráfico) | ativo, tempo gráfico, open_time, OHLCV, fonte |
| `preco.tick` | coletores | api (gráfico ao vivo), decisão (janela de entrada) | ativo, preço, horário da fonte, horário de recebimento |
| `features.prontas` | motor-analise | motor-sinais | id do snapshot, ativo, t |
| `sinal.emitido` | motor-sinais | api, liquidador | id do sinal |
| `sinal.liquidado` | liquidador | api, monitor | id do sinal, resultado |
| `trava.alterada` | monitor, admin | motor-sinais, api | ativo, expiração, ligado/desligado, motivo |
| `dados.qualidade` | qualidade | motor-sinais, admin | ativo, janela, tipo de problema |

- **Frontend ↔ backend:** REST para consultas e comandos. Um WebSocket por usuário logado, multiplexado: o cliente se inscreve em canais (`grafico:BTCUSDT:1m`, `sinais:BTCUSDT`). O servidor valida sessão e assinatura na conexão e em cada inscrição, e encerra a conexão quando a sessão é revogada ou a assinatura vence.
- **Uma conexão externa por fonte, não por usuário:** todos os usuários recebem dados pelo fan-out do Redis. Isso atende ao requisito de não abrir conexões desnecessárias.

## 11. Banco de dados (estrutura inicial)

Tabelas principais (PostgreSQL 18 + TimescaleDB; `ts` = timestamptz em UTC):

**Mercado**
- `assets` — id, símbolo interno, classe (cripto, forex, metal, ação), provedor, símbolo no provedor, precisão de preço, ativo.
- `asset_calendars` — ativo, regras de sessão (fuso de origem, abertura, fechamento, feriados), usando biblioteca de calendário de bolsas para ações.
- `candles_1m` (hypertable) — PK (asset_id, open_time); open, high, low, close, volume, quote_volume, trades, taker_buy_volume, fonte, ingested_at. Só candles fechados.
- `candles_1s` (hypertable, só cripto) — mesma estrutura. Usada para liquidação e períodos em segundos.
- `quotes` (hypertable, forex/metais) — asset_id, ts, bid, ask. Usada para liquidação desses ativos.
- `data_quality_events` — ativo, início, fim, tipo, detalhes.
- Tempos gráficos maiores: continuous aggregates do TimescaleDB a partir de `candles_1m`.

**Inteligência**
- `feature_snapshots` (hypertable) — asset_id, timeframe, ts, feature_set_version, features (JSONB). Exportado para Parquet no laboratório.
- `model_versions` — id, expiração, tipo, hiperparâmetros, período de treino, feature_set_version, métricas, status (desafiante, campeão, aposentado), uri do artefato, criado_em.
- `validation_reports` — model_version, ativo, expiração, período, n, taxa de acerto, limite inferior de Wilson 95%, `p*`, aprovado, detalhes (JSONB).
- `signal_gates` — ativo, expiração, model_version, ligado, motivo, atualizado_por, atualizado_em. **É a trava: sem linha ligada, só AGUARDAR.**
- `signals` — id (UUID v7), asset_id, expiração (s), direção (BUY, SELL, WAIT), gerado_em (ms), preço de referência, janela_ate, tolerância de preço, probabilidade, calibrada (bool), n de validação, model_version_id, strategy_version, condições (JSONB), invalidação (JSONB), explicação, feature_snapshot_id, motivo_espera (para WAIT).
- `signal_outcomes` — signal_id, vencimento, preço de liquidação, resultado (WIN, LOSS, TIE, NO_DATA), apertado (bool), margem, liquidado_em.

**Corretoras**
- `brokers` — id, nome, notas.
- `broker_assets` — broker_id, asset_id, símbolo na corretora, expirações permitidas, regra de empate, horários, diferença de preço observada.
- `broker_payouts` — broker_asset_id, expiração, faixa de horário (opcional), payout, válido_de, válido_até. **[Arquiteto]** O payout tem dimensão de expiração e de horário desde o início, para não exigir migração se a corretora variar por esses eixos. O `p*` de cada sinal usa o payout vigente quando ele foi emitido.
- `broker_price_checks` — conferência manual no admin: ativo, instante, preço visto na Exnova, preço de referência, diferença. **[Arquiteto]** Formulário simples, sem captura automática. Meta: pelo menos 30 conferências por ativo durante o teste ao vivo, priorizando 1 e 5 min.

**Contas e comercial**
- `users` — id, email (único), password_hash (Argon2id), nome, papel, status (ativo, bloqueado, desativado), totp_secret (cifrado, admin), criado_em.
- `sessions` — id opaco (hash), user_id, criado_em, último uso, ip, user agent, revogada.
- `plans` — id, nome, duração (dias), preço, limites (sessões simultâneas, ativos e recursos permitidos) em JSONB, ativo.
- `subscriptions` — user_id, plan_id, início, fim, status, origem (manual ou gateway futuro).
- `payments` — preparado para gateway futuro: subscription_id, valor, status, referência externa.
- `access_logs` — user_id, ts, evento (login, falha, logout), ip.
- `audit_log` — admin_id, ação, alvo, antes e depois (JSONB), ts.
- `user_settings` — user_id, modo (essencial, avançado), layouts de gráfico, parâmetros de indicadores (JSONB).
- `drawings` — user_id, asset_id, timeframe, payload (JSONB).
- V1.1: `courses`, `lessons`, `lesson_assets`, `quizzes`, `lesson_progress`.

Regras: toda consulta de dado de usuário filtra por `user_id` da sessão. Testes de autorização cobrem o acesso cruzado entre usuários.

## 12. Fluxo de dados: da fonte ao sinal

1. **Coleta.** O coletor mantém uma conexão de streams combinados (klines 1s e 1m e trade agregado para BTC e ETH; quotes do provedor para forex e metais). No início e após cada reconexão, ele **preenche lacunas por REST** antes de liberar dados ao vivo.
2. **Fechamento.** Só candles com marcação de fechado entram no banco e geram `candle.fechado`. Candles em formação vão só para o gráfico, marcados como parciais.
3. **Qualidade.** Gap, atraso acima do limite ou desvio de relógio acima do limite marcam a janela como não confiável. Nessas janelas a decisão retorna AGUARDAR com motivo "dados instáveis".
4. **Análise.** No fechamento do candle de 1m (e dos maiores, quando fecham), o motor calcula os motores e monta o snapshot de features com dados **até `t` inclusive e nada depois**.
5. **Decisão.** Para cada expiração do ativo:
   - mercado aberto e dentro da janela de liquidação do vencimento?
   - trava ligada para (ativo, expiração, modelo)?
   - filtros desfavoráveis (volatilidade fora da faixa validada, notícia de alto impacto no calendário, para forex e metais, **[Arquiteto]** V1.1)?
   - o modelo campeão gera a probabilidade, calibrada, de alta em `t + atraso + expiração` em relação a `t + atraso`;
   - COMPRA se `p_cal ≥ limiar_compra`, VENDA se `1 − p_cal ≥ limiar_venda`, senão AGUARDAR. Os limiares de cada combinação vêm da validação e estão sempre acima de `p*` com margem.
6. **Janela de entrada.** **[Cliente]** Na Exnova, o vencimento de 1 min é **alinhado ao relógio**: uma compra feita entre 00:30:01 e 00:30:29 vence às 00:31:00. Depois do corte, a compra passa para o vencimento seguinte (comprada às 00:30:35, vence às 00:32:00, com cerca de 1:25 restante). Regra geral: o vencimento é o primeiro minuto cheio com pelo menos 30 s restantes. Por isso o sinal de 1 min é decidido no fechamento do candle (00:30:00), a janela de tempo vai até o corte de compra da corretora (00:30:29, menos uma margem de segurança de latência) e o vencimento é o próximo minuto cheio. O modo de vencimento (alinhado ao relógio com corte, ou duração fixa a partir da entrada) e o corte de compra são configurações de cada expiração em `broker_assets`. **[Cliente]** A de 15 min também é alinhada ao relógio: os vencimentos são em horários cheios de 15 em 15 minutos e a compra fecha 5 minutos antes do vencimento (por exemplo, vencimento 00:45, compra liberada até 00:40). **[Arquiteto]** Para expirações com janela longa de compra, o sinal mira um **vencimento fixo** (00:45) e pode ser emitido em qualquer fechamento de candle de 1 min dentro da janela de compra, quando as condições forem atendidas. O tempo restante até o vencimento é uma feature do modelo. Depois de emitido, vale a regra de um sinal ativo por combinação. Grade e corte de 5 min, 30 min e 1 h: **a confirmar na Exnova antes da Fase 5** e cadastrados como configuração. Até lá, a hipótese de trabalho é a mesma lógica (grade do próprio prazo, corte proporcional). Preço: tolerância de `k × ATR` do tempo gráfico de 1m. Fora de qualquer um dos dois, o cartão muda para "Fora da janela, não entre".
7. **Publicação.** O sinal é gravado (inclusive AGUARDAR) e enviado por WebSocket aos usuários com acesso ao ativo. **[Arquiteto]** No máximo **um sinal ativo por ativo × expiração**: enquanto um COMPRA/VENDA não vence, a mesma combinação não emite outro. A tela mostra esse sinal ativo até o vencimento. Isso evita sinais sobrepostos e correlacionados e mantém a tela limpa.
8. **Liquidação.** No vencimento, o liquidador busca o preço de referência:
   - **Cripto:** fechamento do candle de 1 s que termina no segundo do vencimento. **[Arquiteto]**
   - **Forex e metais:** ponto médio da última quote até o instante do vencimento.
   - Sem dado dentro de uma tolerância (por exemplo, 2 s): NO_DATA, fora das estatísticas de acerto e contado à parte.
   - **Apertado:** |preço de liquidação − preço de entrada| < `m × spread típico ou volatilidade de 1 s` do ativo. Reportado com e sem.
9. **Monitoramento.** O monitor atualiza o desempenho ao vivo por combinação. Se o limite superior do intervalo de confiança de Wilson (95%) nos últimos N sinais ficar abaixo de `p*`, a trava é desligada e o admin é alertado.
10. **Aprendizado.** O agendador retreina periodicamente (por exemplo, semanalmente) com todos os dados até a data, gera um desafiante, roda a validação e promove só se aprovado.

## 13. Validação, calibração e trava

### 13.1 Simulação sem vazamento
- **Instante de decisão** = fechamento do candle `t` + atraso de processamento simulado.
- **Entrada simulada** = primeiro preço de referência **depois** do instante de decisão + latência de entrega medida (no mínimo 1 s). Nunca o fechamento do próprio candle usado no cálculo.
- **Rótulo** = direção do preço de referência no vencimento, com a mesma regra da liquidação ao vivo, incluindo empate e apertado. Com vencimento alinhado ao relógio, o vencimento simulado é o mesmo instante fixo usado ao vivo (por exemplo, 00:31:00 para qualquer entrada entre 00:30:01 e 00:30:29). A entrada simulada é sorteada dentro da janela permitida, para o resultado não depender de uma entrada perfeita no primeiro segundo.
- Features só com candles **fechados** até `t`, em todos os tempos gráficos.

### 13.2 Walk-forward
- Janelas: treino de M meses → calibração de 1 mês → teste de 1 mês, avançando mês a mês.
- **Purga e embargo:** amostras de treino cujo rótulo se sobrepõe ao período de teste são removidas, com embargo de pelo menos uma expiração mais o maior lookback.
- **Holdout final:** os 3 meses mais recentes ficam intocados até a avaliação final de cada ciclo.

### 13.3 Critérios para ligar uma combinação (ativo × expiração)
Uma combinação só é ligada se, **no conjunto fora da amostra agregado do walk-forward e no holdout**:
1. n ≥ 300 sinais **não sobrepostos** (a simulação aplica a mesma regra de um sinal ativo por combinação usada ao vivo, então cada sinal conta como uma amostra independente do período do anterior; valor mínimo ajustável);
2. o limite inferior de Wilson 95% da taxa de acerto, excluindo NO_DATA e com empates pela regra da corretora, for maior que `p* + 1 ponto percentual`;
3. o resultado for melhor do que todas as baselines (comprar sempre, vender sempre, seguir o último candle, aleatório com a mesma frequência de sinais);
4. o desempenho não se concentrar em uma janela só (pelo menos 70% das janelas mensais acima de `p*`);
5. houver correção para comparações múltiplas (Benjamini-Hochberg sobre todas as combinações testadas). Muitas combinações testadas fazem algumas parecerem boas só por sorte.

### 13.4 Calibração
- Isotônica ou Platt, escolhida por Brier score na fatia de calibração.
- Diagrama de confiabilidade em cada relatório. A probabilidade só aparece na tela se o erro de calibração esperado (ECE) estiver abaixo de um limite (por exemplo, 2 p.p.).

### 13.5 Champion/challenger
- O desafiante passa pelos critérios de 13.3 **e** precisa superar o campeão no mesmo período fora da amostra, com diferença significativa. Só então é promovido.
- Tudo é registrado em `model_versions` e `validation_reports`. Todo sinal guarda a versão do modelo e da estratégia.

### 13.6 Teste ao vivo antes de cobrar
- De 60 a 90 dias de sinais ao vivo, liquidados automaticamente, sem clientes pagantes.
- Uma combinação só entra no lançamento se também passar nesse período (critérios 1 e 2 com o n disponível, ou n mínimo reduzido e declarado).

## 14. Estratégia de testes

| Nível | O que cobre | Ferramentas |
|---|---|---|
| Unitário | Cada indicador, padrão e detector, agregação de candles, calendário, regras de janela e liquidação. | pytest |
| Valores de referência | Indicadores conferidos contra TA-Lib/pandas-ta e contra casos calculados à mão. Tolerância numérica explícita. | pytest + fixtures |
| Propriedades | Agregação (soma de volume, máxima e mínima), invariância a reordenação de entrada, idempotência da coleta. | Hypothesis |
| **Regressão de vazamento** | Para qualquer `t`, as features em `t` são idênticas quando todos os dados depois de `t` são removidos ou embaralhados. Na simulação, a entrada é sempre posterior à decisão. | pytest (obrigatório no CI) |
| Integração | PostgreSQL/TimescaleDB e Redis reais em contêiner. Reprodução de streams gravados da Binance (incluindo desconexão, mensagem duplicada e servidor desligando). | Testcontainers |
| Contrato | Respostas da API conferidas com o esquema OpenAPI. Tipos do frontend gerados a partir dele. | schemathesis, openapi-typescript |
| Autorização | Matriz papel × plano × endpoint. Usuário A nunca lê dado de B. Assinatura vencida perde acesso na hora, em REST e em WebSocket. | pytest |
| Ponta a ponta | Login, tela do ativo, sinal ao vivo simulado, admin. | Playwright |
| Carga | 2.000 conexões WebSocket simultâneas recebendo ticks e sinais. Latência p99 do evento ao navegador abaixo de 500 ms. | k6 ou Locust |
| Segurança | Varredura de dependências, análise estática, cabeçalhos, rate limit, brute force no login. | pip-audit, npm audit, Bandit, ZAP |

Metas: cobertura ≥ 90% em `analise`, `features`, `backtest`, `decisao`, `liquidacao` e `contas`; ≥ 80% no restante. Nenhuma fase é aprovada com teste falhando ou pulado sem justificativa registrada.

## 15. Segurança e conformidade

- Segredos (chaves de API dos provedores, chaves de cifra) só no backend, por variáveis de ambiente ou gerenciador de segredos. Nunca no frontend nem no repositório.
- Argon2id para senhas. Bloqueio progressivo após falhas de login. Rate limit por IP e por conta. CAPTCHA após falhas repetidas.
- 2FA TOTP obrigatório para admin. Toda ação do admin registrada em `audit_log`.
- Limite de sessões simultâneas por plano (padrão **[Arquiteto]**: 1 sessão ativa, e o login novo derruba a anterior). Isso reduz o compartilhamento de contas.
- HTTPS obrigatório, HSTS, CSP, cookies Secure/httpOnly/SameSite, proteção CSRF nas mutações.
- LGPD: política de privacidade, base legal, exportação e exclusão de dados do usuário, retenção definida dos logs de acesso.
- Aviso de risco permanente e aceite dos termos no primeiro acesso. Texto revisado pelo advogado.

## 16. Riscos

| Risco | Tipo | Impacto | Mitigação |
|---|---|---|---|
| Não existir vantagem em nenhuma combinação | Financeiro / produto | Muito alto | Validar primeiro (Fases 3 a 6). O produto continua útil como painel de análise. Decisão de continuidade ao fim da Fase 6. |
| Ação da CVM ou de órgão de defesa do consumidor | Regulatório | Muito alto | Parecer jurídico antes de vender. Termos, avisos, sem promessa de retorno, sem afiliação a corretoras. |
| Divergência de preço com a Exnova | Técnico / financeiro | Alto em 1 a 2 min | Marcação de apertados, conferência amostral no admin, expirações curtas só se passarem com margem. |
| Sobreajuste e comparações múltiplas | Técnico | Alto | Purga, embargo, holdout, Benjamini-Hochberg, baselines, teste ao vivo. |
| Vazamento de dados no backtest | Técnico | Alto | Código único, testes de regressão de vazamento no CI. |
| Custo de dados de forex e metais | Financeiro | Médio | V1 só com BTC e ETH, com dados gratuitos. Outros ativos só quando houver orçamento. |
| Bloqueio ou mudança de termos da Binance | Técnico / legal | Médio | Hospedagem em região permitida, interface de provedor para trocar de fonte, revisão dos termos de uso de dados. |
| Falha ou instabilidade de dados ao vivo | Técnico | Médio | Qualidade de dados com AGUARDAR automático, reconexão, preenchimento por REST, alertas. |
| Compartilhamento de contas | Comercial | Médio | Limite de sessões e monitoramento de IPs. |
| Usuário perder dinheiro e culpar o produto | Reputação / legal | Alto | Probabilidades honestas, histórico público com derrotas, gestão de risco, avisos. |
| Latência entre a emissão e a entrada do usuário | Técnico | Alto em 1 min | Medição de ponta a ponta, janela calculada com a latência real, desligamento de 1 min se não for viável. |

## 17. Roadmap

As 12 fases originais foram reordenadas para validar primeiro (melhoria aceita). Cada fase segue o ciclo: objetivo → planejamento → implementação → testes → auditoria → documentação → aprovação do cliente. **Nenhuma fase começa sem aprovação da anterior.**

| Fase | Nome | Entregáveis principais | Critério de aprovação |
|---|---|---|---|
| 1 | Planejamento e arquitetura | Este documento, `PROGRESSO.md` | Aprovação do cliente |
| 2 | Estrutura inicial | Monorepo, Docker Compose (Postgres+Timescale, Redis), CI (lint, tipos, testes), logs estruturados, `core` com relógio e calendário | CI verde, ambiente sobe com um comando, testes de `core` passando |
| 3 | Dados de mercado | Coletor Binance para BTC e ETH (histórico desde, no mínimo, 2 anos atrás, e ao vivo), qualidade de dados, agregação de tempos gráficos. A interface de provedor fica pronta para forex e metais, mas a escolha e a contratação do provedor só acontecem quando houver orçamento. | Histórico completo sem gaps não explicados. Agregação idêntica aos klines oficiais. 72 h ao vivo sem perda. Relatório de qualidade. |
| 4 | Motores de análise | Indicadores, padrões, price action, estrutura, regiões, volume, Fibonacci, snapshot de features | Testes de referência e de propriedades. Teste de vazamento verde. |
| 5 | Backtesting e validação | Simulador, walk-forward purgado, baselines, relatórios por ativo, expiração, horário e regime | Reprodutibilidade (mesmo resultado com a mesma semente). Testes de vazamento. Relatório das baselines. |
| 6 | Modelos e calibração | LightGBM por expiração, calibração, registro, champion/challenger. **[Arquiteto]** Em paralelo: parecer jurídico encomendado. | **Relatório de decisão:** quais combinações passam nos critérios de 13.3. O cliente decide seguir, ajustar ou parar, já com o parecer jurídico em mãos. |
| 7 | Motor de sinais ao vivo | Decisão, janela de entrada, liquidação, monitor e trava, explicação por template | Sinais ao vivo gravados e liquidados. Início do período de 60 a 90 dias de teste. |
| 8 | Contas e autenticação | Usuários, sessões, papéis, planos, assinaturas no backend | Matriz de autorização 100% verde. Testes de segurança. |
| 9 | Plataforma web | Gráficos, tela do ativo, painel de sinais, histórico, modos Essencial e Avançado, configurações salvas | E2E verde. Latência medida. Revisão visual pelo cliente. |
| 10 | Administração | Painel admin completo, payout por corretora, travas, auditoria | E2E admin verde |
| 11 | Segurança, carga, legal e lançamento V1 | Testes de carga e de segurança, termos e LGPD revisados pelo advogado, observabilidade em produção | **Portões:** teste ao vivo concluído e aprovado + parecer jurídico favorável (obtido na Fase 6) + carga atendida |
| 12 | V1.1 | Prata, ações, mais pares, expirações 2, 3 e 10 min, cursos, notificações | Por item, com o mesmo processo de validação |

As Fases 8 a 10 podem andar durante o período de teste ao vivo iniciado na Fase 7, sem afetá-lo.

## 18. Deixado para o construtor

- Nomes exatos de classes e funções, organização interna de cada módulo.
- Versões exatas fixadas no lock, desde que respeitem as séries da seção 7.2.
- Hiperparâmetros iniciais e espaço de busca do LightGBM.
- Valores iniciais de `J(expiração)`, `k` (tolerância de preço) e `m` (faixa de apertado), a calibrar com dados.
- Layout detalhado das telas, seguindo a referência de tema escuro e o esboço do cartão de sinal.
- Visibilidade do histórico **[Arquiteto]**: o histórico completo de sinais fica disponível para assinantes. Uma página pública mostra só estatísticas agregadas por ativo e expiração (n, taxa de acerto, período), sem sinais individuais recentes.
- Conteúdo de cada plano: definido na Fase 10. Até lá, a matriz de autorização usa permissões por recurso (`ativos`, `expirações`, `modo_avancado`, `cursos`), que os planos combinam.

## 19. Questões em aberto

Respondidas após a revisão independente:
- Vencimento na Exnova: alinhado ao relógio, com prazo de compra. 1 min com 30 s de corte e 15 min com 5 min de corte, confirmados (§12.6).
- Orçamento de dados: zero no início, então a V1 cobre só BTC e ETH (§6).
- Empate: devolve o valor (§3).

Pendentes, sem bloquear a aprovação do design:
1. **Mercado de venda e país da empresa** (só residentes no Brasil ou também outros países). Define o escopo do parecer jurídico da Fase 6.
2. **Payout atual de BTC e ETH na Exnova, por expiração.** Cadastrado como configuração antes da Fase 5.
3. **Corte de compra de 5 e 30 min e de 1 h na Exnova.** Cadastrado como configuração antes da Fase 5.
4. **Conteúdo e preço dos planos.** Definidos na Fase 10.

## Fontes consultadas

- Binance Spot — WebSocket Streams (limites, klines, 24 h): https://developers.binance.com/docs/binance-spot-api-docs/web-socket-streams
- Next.js 16: https://nextjs.org/blog/next-16 · Next.js 16.3: https://nextjs.org/blog/next-16-3
- Lightweight Charts 5: https://www.tradingview.com/blog/en/tradingview-lightweight-charts-version-5-50837
- FastAPI — notas de versão: https://fastapi.tiangolo.com/release-notes/ · fixação de versão: https://fastapi.tiangolo.com/deployment/versions/
- TimescaleDB — versões e suporte a PostgreSQL: https://github.com/timescale/timescaledb/releases
- Quadcode como plataforma da IQ Option e da Exnova: https://financemagnates.com/thought-leadership/quadcode-saas-a-broker-out-of-the-box
- IQ Option — guia de Opções Binárias (prazo de compra, empate, payout): https://blog.iqoption.com/pt/como-negociar-opcoes-binarias-um-guia-de-a-a-z-da-iq-option/
- CVM — decisões e alertas sobre opções binárias: https://conteudo.cvm.gov.br/export/sites/cvm/decisoes/anexos/2022/20221108/2718_22.pdf
