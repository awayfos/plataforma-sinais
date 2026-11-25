#!/usr/bin/env bash
# Teste de fumaça: sobe o ambiente completo, coleta dados reais da Binance por ~90 s
# e confere que candles fechados chegaram ao banco e ao Redis.
set -euo pipefail
cd "$(dirname "$0")/.."
COMPOSE="docker compose -f infra/docker-compose.yml --env-file ${ENV_FILE:-.env.example}"
$COMPOSE up -d --build
trap '$COMPOSE logs --tail=50 coletor; $COMPOSE down -v' EXIT
for i in $(seq 1 90); do
  n=$($COMPOSE exec -T db psql -U sinais -d sinais -tAc "SELECT count(*) FROM candles_1m" 2>/dev/null || echo 0)
  if [ "${n:-0}" -gt 0 ] && [ "$i" -gt 70 ]; then break; fi
  sleep 1
done
m1=$($COMPOSE exec -T db psql -U sinais -d sinais -tAc "SELECT count(*) FROM candles_1m")
s1=$($COMPOSE exec -T db psql -U sinais -d sinais -tAc "SELECT count(*) FROM candles_1s")
ev=$($COMPOSE exec -T redis redis-cli XLEN candle.fechado)
echo "candles_1m=$m1 candles_1s=$s1 eventos_candle_fechado=$ev"
[ "$m1" -gt 0 ] && [ "$s1" -gt 0 ] && [ "$ev" -gt 0 ]
