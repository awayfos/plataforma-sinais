# Infraestrutura

Serviços locais: PostgreSQL 18 + TimescaleDB (`db`), Redis 8 (`redis`) e o backend.

```bash
cp .env.example .env                       # na raiz do repositório
docker compose -f infra/docker-compose.yml --env-file .env up -d --build
docker compose -f infra/docker-compose.yml --env-file .env logs backend   # deve imprimir "sinais 0.1.0 ok"
```

As portas ficam presas a `127.0.0.1`. Valide o arquivo sem subir nada:

```bash
docker compose -f infra/docker-compose.yml --env-file .env.example config -q
```

## API e motor de análise

- `api` (FastAPI) escuta em `127.0.0.1:8000`. `motor_analise` consome `candle.fechado` e publica `analise.atualizada`.
- `SINAIS_CHAVE_CIFRA` (32 bytes em base64) cifra o segredo TOTP dos admins. A do `.env.example` é só para desenvolvimento.
- Criar o primeiro admin (a senha vem de `SINAIS_ADMIN_SENHA` ou é pedida no terminal; a saída é a URI `otpauth://` para o autenticador):

```bash
docker compose -f infra/docker-compose.yml --env-file .env exec api \
  python -m sinais.processos.criar_admin --email admin@exemplo.com
```

- **Produção atrás de proxy (Next rewrite, nginx):**
  - `SINAIS_AMBIENTE=prod` exige `SINAIS_ORIGENS_PERMITIDAS` (ex.: `https://app.exemplo.com`) e recusa a chave de cifra do `.env.example`.
  - `SINAIS_PROXIES_CONFIAVEIS` lista os CIDRs dos proxies (ex.: `127.0.0.1/32,172.16.0.0/12`). Só conexões vindas deles têm o `X-Forwarded-For` lido, da direita para a esquerda, pulando os proxies; o IP do cliente é o primeiro de fora. Sem isso, todos os usuários aparecem com o IP do proxy e dividem o mesmo limite de login.
  - O `Origin` do WebSocket precisa estar em `SINAIS_ORIGENS_PERMITIDAS`; o `X-Forwarded-Host` só é considerado quando a conexão vem de um proxy confiável.
  - O nginx deve repassar `X-Forwarded-For` com `$proxy_add_x_forwarded_for` e o `Upgrade` do WebSocket.
- Desenvolvimento: o padrão aceita o frontend em `http://localhost:3000`.
- `infra/fumaca.sh` sobe tudo, cria admin e cliente pela API e confere `/api/candles`, `/api/analise` e `/api/sinais`.
