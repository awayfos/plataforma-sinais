# Relatório do laboratório

## Hipóteses e fonte

- **fonte:** data.binance.vision, klines de 1m, 2024-11 a 2026-10; 1s nos últimos 2 meses
- **payout:** 0.85 (hipotético até o cliente informar o da Exnova)
- **preço (linhas sem '(1s)'):** 1m: entrada = abertura do minuto da decisão, sem latência; LIMITE SUPERIOR otimista para expirações curtas
- **preço (linhas '(1s)'):** 1s: entrada sorteada entre decisão + 2 s e o prazo de compra; vencimento = fechamento do candle de 1 s que termina no vencimento
- **apertado:** diferença de preço menor que 0,01% do preço (a corretora pode divergir)
- **latência:** 2 s (checada contra o prazo de compra)
- **cortes 5m/30m/1h:** hipóteses (1/3 da grade) até confirmar na Exnova
- **lacunas:** nenhuma

## Resultados

| Ativo | Expiração | Estratégia | Decididas | Empates | Sem dado | Fora da janela | Apertados | Taxa | Taxa s/ apertados | Wilson inf. | Equilíbrio | Valor esperado | Meses acima | Aprovada |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BTCUSDT | 1m | sempre_compra | 1015817 | 35382 | 1 | 0 | 270485 | 50.06% | 50.06% | 49.96% | 54.05% | -0.0714 | 0.00% | não |
| BTCUSDT | 1m | sempre_venda | 1015817 | 35382 | 1 | 0 | 270485 | 49.94% | 49.94% | 49.84% | 54.05% | -0.0735 | 0.00% | não |
| BTCUSDT | 1m | seguir_ultimo | 987342 | 29318 | 1 | 0 | 251242 | 50.81% | 50.49% | 50.71% | 54.05% | -0.0582 | 0.00% | não |
| BTCUSDT | 1m | aleatoria | 1015817 | 35382 | 1 | 0 | 270485 | 49.93% | 49.94% | 49.84% | 54.05% | -0.0737 | 0.00% | não |
| BTCUSDT | 5m | sempre_compra | 209606 | 634 | 1 | 0 | 22853 | 49.94% | 49.91% | 49.72% | 54.05% | -0.0760 | 0.00% | não |
| BTCUSDT | 5m | sempre_venda | 209606 | 634 | 1 | 0 | 22853 | 50.06% | 50.09% | 49.85% | 54.05% | -0.0736 | 0.00% | não |
| BTCUSDT | 5m | seguir_ultimo | 209446 | 708 | 1 | 0 | 23076 | 49.60% | 49.53% | 49.38% | 54.05% | -0.0822 | 0.00% | não |
| BTCUSDT | 5m | aleatoria | 209606 | 634 | 1 | 0 | 22853 | 49.95% | 49.92% | 49.74% | 54.05% | -0.0756 | 0.00% | não |
| BTCUSDT | 15m | sempre_compra | 70036 | 44 | 1 | 0 | 3766 | 49.86% | 50.00% | 49.49% | 54.05% | -0.0775 | 0.00% | não |
| BTCUSDT | 15m | sempre_venda | 70036 | 44 | 1 | 0 | 3766 | 50.14% | 50.00% | 49.77% | 54.05% | -0.0724 | 0.00% | não |
| BTCUSDT | 15m | seguir_ultimo | 70033 | 47 | 1 | 0 | 3783 | 49.73% | 49.75% | 49.36% | 54.05% | -0.0800 | 0.00% | não |
| BTCUSDT | 15m | aleatoria | 70036 | 44 | 1 | 0 | 3766 | 50.16% | 50.12% | 49.79% | 54.05% | -0.0720 | 0.00% | não |
| BTCUSDT | 30m | sempre_compra | 35028 | 12 | 1 | 0 | 1363 | 50.66% | 50.66% | 50.14% | 54.05% | -0.0628 | 0.00% | não |
| BTCUSDT | 30m | sempre_venda | 35028 | 12 | 1 | 0 | 1363 | 49.34% | 49.34% | 48.82% | 54.05% | -0.0872 | 0.00% | não |
| BTCUSDT | 30m | seguir_ultimo | 35029 | 11 | 1 | 0 | 1369 | 50.16% | 50.10% | 49.64% | 54.05% | -0.0720 | 0.00% | não |
| BTCUSDT | 30m | aleatoria | 35028 | 12 | 1 | 0 | 1363 | 50.33% | 50.31% | 49.81% | 54.05% | -0.0688 | 0.00% | não |
| BTCUSDT | 60m | sempre_compra | 17518 | 2 | 1 | 0 | 521 | 50.34% | 50.34% | 49.60% | 54.05% | -0.0688 | 0.00% | não |
| BTCUSDT | 60m | sempre_venda | 17518 | 2 | 1 | 0 | 521 | 49.66% | 49.66% | 48.92% | 54.05% | -0.0812 | 0.00% | não |
| BTCUSDT | 60m | seguir_ultimo | 17518 | 2 | 1 | 0 | 519 | 49.67% | 49.79% | 48.93% | 54.05% | -0.0810 | 0.00% | não |
| BTCUSDT | 60m | aleatoria | 17518 | 2 | 1 | 0 | 521 | 50.05% | 50.07% | 49.31% | 54.05% | -0.0740 | 0.00% | não |
| BTCUSDT | 1m (1s) | sempre_compra | 81822 | 6017 | 1 | 0 | 33622 | 49.90% | 49.71% | 49.56% | 54.05% | -0.0716 | 0.00% | não |
| BTCUSDT | 1m (1s) | sempre_venda | 81822 | 6017 | 1 | 0 | 33622 | 50.10% | 50.29% | 49.76% | 54.05% | -0.0681 | 0.00% | não |
| BTCUSDT | 1m (1s) | seguir_ultimo | 78694 | 5145 | 1 | 0 | 30847 | 51.11% | 50.70% | 50.77% | 54.05% | -0.0510 | 0.00% | não |
| BTCUSDT | 1m (1s) | aleatoria | 81822 | 6017 | 1 | 0 | 33622 | 49.97% | 49.85% | 49.63% | 54.05% | -0.0704 | 0.00% | não |
| BTCUSDT | 5m (1s) | sempre_compra | 17356 | 212 | 1 | 0 | 3120 | 49.98% | 50.00% | 49.23% | 54.05% | -0.0745 | 0.00% | não |
| BTCUSDT | 5m (1s) | sempre_venda | 17356 | 212 | 1 | 0 | 3120 | 50.02% | 50.00% | 49.28% | 54.05% | -0.0737 | 0.00% | não |
| BTCUSDT | 5m (1s) | seguir_ultimo | 17381 | 178 | 1 | 0 | 3118 | 49.22% | 49.17% | 48.48% | 54.05% | -0.0885 | 0.00% | não |
| BTCUSDT | 5m (1s) | aleatoria | 17356 | 212 | 1 | 0 | 3120 | 50.27% | 50.15% | 49.52% | 54.05% | -0.0693 | 0.00% | não |
| ETHUSDT | 1m | sempre_compra | 1038073 | 13126 | 1 | 0 | 173004 | 50.23% | 50.22% | 50.14% | 54.05% | -0.0698 | 0.00% | não |
| ETHUSDT | 1m | sempre_venda | 1038073 | 13126 | 1 | 0 | 173004 | 49.77% | 49.78% | 49.67% | 54.05% | -0.0783 | 0.00% | não |
| ETHUSDT | 1m | seguir_ultimo | 1026158 | 12001 | 1 | 0 | 168132 | 49.65% | 49.49% | 49.55% | 54.05% | -0.0805 | 0.00% | não |
| ETHUSDT | 1m | aleatoria | 1038073 | 13126 | 1 | 0 | 173004 | 49.95% | 49.94% | 49.86% | 54.05% | -0.0749 | 0.00% | não |
| ETHUSDT | 5m | sempre_compra | 209790 | 450 | 1 | 0 | 14749 | 50.16% | 50.13% | 49.94% | 54.05% | -0.0720 | 0.00% | não |
| ETHUSDT | 5m | sempre_venda | 209790 | 450 | 1 | 0 | 14749 | 49.84% | 49.87% | 49.63% | 54.05% | -0.0777 | 0.00% | não |
| ETHUSDT | 5m | seguir_ultimo | 209768 | 458 | 1 | 0 | 14792 | 49.36% | 49.33% | 49.15% | 54.05% | -0.0866 | 0.00% | não |
| ETHUSDT | 5m | aleatoria | 209790 | 450 | 1 | 0 | 14749 | 50.06% | 50.07% | 49.85% | 54.05% | -0.0737 | 0.00% | não |
| ETHUSDT | 15m | sempre_compra | 70016 | 64 | 1 | 0 | 2532 | 50.38% | 50.37% | 50.01% | 54.05% | -0.0678 | 0.00% | não |
| ETHUSDT | 15m | sempre_venda | 70016 | 64 | 1 | 0 | 2532 | 49.62% | 49.63% | 49.25% | 54.05% | -0.0820 | 0.00% | não |
| ETHUSDT | 15m | seguir_ultimo | 70016 | 64 | 1 | 0 | 2540 | 49.90% | 49.90% | 49.53% | 54.05% | -0.0767 | 0.00% | não |
| ETHUSDT | 15m | aleatoria | 70016 | 64 | 1 | 0 | 2532 | 50.21% | 50.17% | 49.84% | 54.05% | -0.0711 | 0.00% | não |
| ETHUSDT | 30m | sempre_compra | 35010 | 30 | 1 | 0 | 1003 | 50.57% | 50.59% | 50.05% | 54.05% | -0.0644 | 0.00% | não |
| ETHUSDT | 30m | sempre_venda | 35010 | 30 | 1 | 0 | 1003 | 49.43% | 49.41% | 48.91% | 54.05% | -0.0855 | 0.00% | não |
| ETHUSDT | 30m | seguir_ultimo | 35010 | 30 | 1 | 0 | 1012 | 49.62% | 49.56% | 49.10% | 54.05% | -0.0820 | 0.00% | não |
| ETHUSDT | 30m | aleatoria | 35010 | 30 | 1 | 0 | 1003 | 50.41% | 50.39% | 49.88% | 54.05% | -0.0674 | 0.00% | não |
| ETHUSDT | 60m | sempre_compra | 17515 | 5 | 1 | 0 | 360 | 50.57% | 50.63% | 49.83% | 54.05% | -0.0644 | 0.00% | não |
| ETHUSDT | 60m | sempre_venda | 17515 | 5 | 1 | 0 | 360 | 49.43% | 49.37% | 48.69% | 54.05% | -0.0856 | 0.00% | não |
| ETHUSDT | 60m | seguir_ultimo | 17516 | 4 | 1 | 0 | 361 | 49.49% | 49.51% | 48.75% | 54.05% | -0.0844 | 0.00% | não |
| ETHUSDT | 60m | aleatoria | 17515 | 5 | 1 | 0 | 360 | 49.99% | 49.97% | 49.25% | 54.05% | -0.0751 | 4.17% | não |
| ETHUSDT | 1m (1s) | sempre_compra | 84847 | 2992 | 1 | 0 | 23943 | 49.95% | 49.79% | 49.61% | 54.05% | -0.0733 | 0.00% | não |
| ETHUSDT | 1m (1s) | sempre_venda | 84847 | 2992 | 1 | 0 | 23943 | 50.05% | 50.21% | 49.71% | 54.05% | -0.0716 | 0.00% | não |
| ETHUSDT | 1m (1s) | seguir_ultimo | 83316 | 2716 | 1 | 0 | 22985 | 50.00% | 49.82% | 49.66% | 54.05% | -0.0726 | 0.00% | não |
| ETHUSDT | 1m (1s) | aleatoria | 84847 | 2992 | 1 | 0 | 23943 | 50.06% | 49.95% | 49.72% | 54.05% | -0.0714 | 0.00% | não |
| ETHUSDT | 5m (1s) | sempre_compra | 17482 | 86 | 1 | 0 | 2191 | 49.68% | 49.70% | 48.94% | 54.05% | -0.0805 | 0.00% | não |
| ETHUSDT | 5m (1s) | sempre_venda | 17482 | 86 | 1 | 0 | 2191 | 50.32% | 50.30% | 49.58% | 54.05% | -0.0687 | 0.00% | não |
| ETHUSDT | 5m (1s) | seguir_ultimo | 17471 | 94 | 1 | 0 | 2258 | 49.87% | 49.65% | 49.13% | 54.05% | -0.0770 | 0.00% | não |
| ETHUSDT | 5m (1s) | aleatoria | 17482 | 86 | 1 | 0 | 2191 | 49.98% | 50.20% | 49.24% | 54.05% | -0.0751 | 0.00% | não |

Aprovação: Benjamini-Hochberg (q = 5%) sobre todas as linhas, pelo menos 300 operações decididas, limite inferior de Wilson acima do equilíbrio + 1 p.p. e pelo menos 70% dos meses civis (com 30+ operações) acima do equilíbrio. Linhas de estratégias complementares são correlacionadas; a exigência extra de Wilson torna a correção conservadora.

##[group]Run actions/upload-artifact@v4
with:
  name: relatorio-laboratorio
  path: backend/relatorio/
  if-no-files-found: warn
  compression-level: 6
  overwrite: false
  include-hidden-files: false
env:
  UV_PYTHON: 3.13
  UV_CACHE_DIR: /home/runner/work/_temp/setup-uv-cache
##[endgroup]
(node:2613) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
(Use `node --trace-deprecation ...` to show where the warning was created)
With the provided path, there will be 2 files uploaded
Artifact name is valid!
Root directory input is valid!
Beginning upload of artifact content to blob storage
(node:2613) [DEP0169] DeprecationWarning: `url.parse()` behavior is not standardized and prone to errors that have security implications. Use the WHATWG URL API instead. CVEs are not issued for `url.parse()` vulnerabilities.
Uploaded bytes 7232
Finished uploading artifact content to blob storage!
SHA256 digest of uploaded artifact zip is 406f789f3fc0dccb4c08fb435b0f38f8d1a8cc3de8746f922e58c5d001083e6e
Finalizing artifact upload
Artifact relatorio-laboratorio.zip successfully finalized. Artifact ID 15006311487
Artifact relatorio-laboratorio has been successfully uploaded! Final size is 7232 bytes. Artifact ID is 15006311487
Artifact download URL: https://github.com/awayfos/plataforma-sinais/actions/runs/45579483505/artifacts/15006311487
Post job cleanup.
Cache hit occurred on key setup-uv-1-x86_64-unknown-linux-gnu-3.13-pruned-e6aacedb1dfa472d6987776d9eaea478fda744b062dda20b9c60ce2b200a5352, not saving cache.
(node:2625) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
(Use `node --trace-deprecation ...` to show where the warning was created)
Post job cleanup.
[command]/usr/bin/git version
git version 2.56.1
Temporarily overriding HOME='/home/runner/work/_temp/ec0c9db2-d90b-472c-bbea-cd30e21e5a6a' before making global git config changes
Adding repository directory to the temporary git global config as a safe directory
[command]/usr/bin/git config --global --add safe.directory /home/runner/work/plataforma-sinais/plataforma-sinais
[command]/usr/bin/git config --local --name-only --get-regexp core\.sshCommand
[command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
[command]/usr/bin/git config --local --name-only --get-regexp http\.https\:\/\/github\.com\/\.extraheader
http.https://github.com/.extraheader
[command]/usr/bin/git config --local --unset-all http.https://github.com/.extraheader
[command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'http\.https\:\/\/github\.com\/\.extraheader' && git config --local --unset-all 'http.https://github.com/.extraheader' || :"
[command]/usr/bin/git config --local --name-only --get-regexp ^includeIf\.gitdir:
[command]/usr/bin/git submodule foreach --recursive git config --local --show-origin --name-only --get-regexp remote.origin.url
Cleaning up orphan processes
##[warning]Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@v4, actions/upload-artifact@v4, astral-sh/setup-uv@v6. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/

Execução: GitHub Actions, workflow "Laboratório", run 45579483505 (2026-11-25), com preços de 1 s nos 2 últimos meses.
