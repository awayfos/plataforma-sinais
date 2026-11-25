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

- `infra/fumaca.sh` sobe tudo, cria admin e cliente pela API e confere `/api/candles`, `/api/analise` e `/api/sinais`.
