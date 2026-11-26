# Contagem de ocorrências do Motor de Situações (sem rótulo)

- **Data:** 2026-11-26. **Feita depois do pré-registro** (`2026-11-26-situacoes-pre-registro.md`, commit `fb8bc3a`) e antes de qualquer rodada rotulada.
- **Rodada:** workflow "Situações", run 45819149884 (jobs BTCUSDT e ETHUSDT), código do commit `d8575fa`. Só klines de 1m; nenhum preço futuro foi olhado.
- **Dados:** Binance spot 1m, 2024-11 a 2026-10, 1.051.200 candles por ativo, sem lacunas. Eventos brutos: BTC 117.906 (1.620 em conflito), ETH 133.294 (1.973 em conflito).
- **Regra de contagem:** sem conflito, janela de compra válida para a entrada sorteada, um sinal por vencimento. Teto para o n da avaliação.
- **Corte pré-registrado:** n nos 14 meses de teste do walk-forward (2025-06 a 2026-07) ≥ 300.

## Resultado

| Ativo | Variação | Espelho | Teste 15m | Teste 5m | Teste 30m | Holdout 15m | Total 15m | Elegível (15m / 5m / 30m) |
|---|---|---|---|---|---|---|---|---|
| BTCUSDT | S1 | topo | 1256 | 1549 | 1209 | 234 | 2222 | sim / sim / sim |
| BTCUSDT | S1 | fundo | 1178 | 1394 | 1116 | 250 | 2071 | sim / sim / sim |
| BTCUSDT | S2 | topo | 13181 | 19724 | 9802 | 2587 | 22677 | sim / sim / sim |
| BTCUSDT | S2 | fundo | 13149 | 19623 | 9757 | 2519 | 22669 | sim / sim / sim |
| BTCUSDT | S3 | topo | 1161 | 1380 | 1136 | 207 | 1923 | sim / sim / sim |
| BTCUSDT | S3 | fundo | 1301 | 1524 | 1247 | 220 | 2174 | sim / sim / sim |
| BTCUSDT | S3b | topo | 671 | 793 | 660 | 121 | 1136 | sim / sim / sim |
| BTCUSDT | S3b | fundo | 815 | 934 | 769 | 128 | 1355 | sim / sim / sim |
| BTCUSDT | S4 | topo | 309 | 352 | 300 | 59 | 529 | sim / sim / sim |
| BTCUSDT | S4 | fundo | 328 | 366 | 315 | 63 | 544 | sim / sim / sim |
| BTCUSDT | S5 | topo | 86 | 129 | 87 | 24 | 155 | não / não / não |
| BTCUSDT | S5 | fundo | 105 | 158 | 108 | 27 | 193 | não / não / não |
| BTCUSDT | S6 | topo | 6 | 7 | 4 | 4 | 18 | não / não / não |
| BTCUSDT | S6 | fundo | 9 | 11 | 8 | 1 | 14 | não / não / não |
| BTCUSDT | S6a | topo | 339 | 406 | 337 | 94 | 657 | sim / sim / sim |
| BTCUSDT | S6a | fundo | 371 | 420 | 368 | 81 | 630 | sim / sim / sim |
| BTCUSDT | S7 | topo | 277 | 275 | 257 | 47 | 462 | não / não / não |
| BTCUSDT | S7 | fundo | 192 | 206 | 189 | 46 | 330 | não / não / não |
| BTCUSDT | S8 | topo | 1491 | 1501 | 1188 | 287 | 2555 | sim / sim / sim |
| BTCUSDT | S8 | fundo | 1139 | 1187 | 929 | 248 | 1966 | sim / sim / sim |
| ETHUSDT | S1 | topo | 1023 | 1280 | 998 | 221 | 1782 | sim / sim / sim |
| ETHUSDT | S1 | fundo | 999 | 1203 | 970 | 183 | 1654 | sim / sim / sim |
| ETHUSDT | S2 | topo | 15154 | 23023 | 10838 | 3064 | 25758 | sim / sim / sim |
| ETHUSDT | S2 | fundo | 14935 | 22921 | 10835 | 3071 | 25716 | sim / sim / sim |
| ETHUSDT | S3 | topo | 1451 | 1763 | 1456 | 256 | 2315 | sim / sim / sim |
| ETHUSDT | S3 | fundo | 1512 | 1840 | 1498 | 298 | 2491 | sim / sim / sim |
| ETHUSDT | S3b | topo | 987 | 1161 | 976 | 176 | 1559 | sim / sim / sim |
| ETHUSDT | S3b | fundo | 981 | 1165 | 981 | 199 | 1613 | sim / sim / sim |
| ETHUSDT | S4 | topo | 349 | 394 | 334 | 64 | 600 | sim / sim / sim |
| ETHUSDT | S4 | fundo | 370 | 414 | 350 | 63 | 595 | sim / sim / sim |
| ETHUSDT | S5 | topo | 73 | 111 | 79 | 24 | 137 | não / não / não |
| ETHUSDT | S5 | fundo | 98 | 141 | 101 | 21 | 157 | não / não / não |
| ETHUSDT | S6 | topo | 7 | 6 | 7 | 0 | 13 | não / não / não |
| ETHUSDT | S6 | fundo | 11 | 12 | 9 | 3 | 17 | não / não / não |
| ETHUSDT | S6a | topo | 366 | 435 | 365 | 90 | 687 | sim / sim / sim |
| ETHUSDT | S6a | fundo | 305 | 352 | 316 | 71 | 539 | sim / sim / sim |
| ETHUSDT | S7 | topo | 274 | 282 | 258 | 65 | 480 | não / não / não |
| ETHUSDT | S7 | fundo | 153 | 154 | 146 | 34 | 265 | não / não / não |
| ETHUSDT | S8 | topo | 1146 | 1218 | 954 | 273 | 2036 | sim / sim / sim |
| ETHUSDT | S8 | fundo | 919 | 960 | 777 | 216 | 1624 | sim / sim / sim |

**Elegíveis: 84 de 120 chaves.** Fora da avaliação confirmatória (abaixo de 300 nos meses de teste, em todas as expirações e nos dois ativos): **S5** (CHoCH após tendência esgotada: 73–158), **S6** (4º toque ou mais na máxima/mínima de 4 h em 15m: 4–12) e **S7** (divergência no extremo de 15m: 146–282). Pela regra do pré-registro elas não são afrouxadas; continuam só como diagnóstico.

Observações (sem efeito na avaliação):

- S6 é muito rara com a regra pré-registrada (zona de 0,15 × ATR de 15m na máxima de 4 h, com todo toque recuando). A variação do cliente S6a (2º–3º toque) tem 305–435 por chave.
- S2 (falso rompimento de região com ≥ 3 toques em 4 h, níveis de pivôs de 1m) é a mais frequente: 9.757–23.023 por chave.
- S4 fica perto do corte (300–414).
