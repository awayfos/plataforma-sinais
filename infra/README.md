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
