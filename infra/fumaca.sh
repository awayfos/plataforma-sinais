#!/usr/bin/env bash
# Teste de fumaça: sobe o ambiente completo, coleta dados reais da Binance, confere candles no
# banco e no Redis, e exercita a API de ponta a ponta: admin com 2FA cria plano e cliente, o
# cliente lê /api/candles, /api/analise e /api/sinais.
set -euo pipefail
cd "$(dirname "$0")/.."
COMPOSE="docker compose -f infra/docker-compose.yml --env-file ${ENV_FILE:-.env.example}"
API=http://127.0.0.1:8000
TMP=$(mktemp -d)
$COMPOSE up -d --build
trap '$COMPOSE logs --tail=50 coletor motor_analise api; $COMPOSE down -v; rm -rf "$TMP"' EXIT

# Espera até 5 min pelos primeiros eventos ao vivo (o histórico é baixado antes).
for i in $(seq 1 300); do
  ev=$($COMPOSE exec -T redis redis-cli XLEN candle.fechado 2>/dev/null || echo 0)
  if [ "${ev:-0}" -gt 5 ]; then break; fi
  sleep 1
done
m1=$($COMPOSE exec -T db psql -U sinais -d sinais -tAc "SELECT count(*) FROM candles_1m")
s1=$($COMPOSE exec -T db psql -U sinais -d sinais -tAc "SELECT count(*) FROM candles_1s")
ev=$($COMPOSE exec -T redis redis-cli XLEN candle.fechado)
echo "candles_1m=$m1 candles_1s=$s1 eventos_candle_fechado=$ev"
{ [ "$m1" -gt 0 ] && [ "$s1" -gt 0 ] && [ "$ev" -gt 0 ]; } || { echo "FALHOU: coleta sem dados"; exit 1; }
echo "Conferência da agregação local contra os candles oficiais da Binance:"
$COMPOSE exec -T coletor python -m sinais.dados.conferencia

echo "== API =="
for i in $(seq 1 120); do
  if curl -fsS "$API/api/publico/estatisticas" >/dev/null 2>&1; then break; fi
  sleep 1
done
curl -fsS "$API/api/publico/estatisticas"; echo

falha() { echo "FALHOU: $*"; [ -f "$TMP/corpo" ] && cat "$TMP/corpo"; echo; exit 1; }

# Requisição JSON; grava o corpo em $TMP/corpo e devolve o status HTTP.
pedir() {  # pedir <método> <rota> <arquivo-de-sessão|-> [corpo]
  local metodo=$1 rota=$2 sessao=$3 corpo=${4:-}
  local args=(-sS -o "$TMP/corpo" -w '%{http_code}' -X "$metodo" -H 'Content-Type: application/json')
  if [ "$sessao" != "-" ]; then
    local token csrf
    token=$(sed -n 1p "$sessao")
    csrf=$(sed -n 2p "$sessao")
    args+=(-H "Cookie: sinais_sessao=$token; sinais_csrf=$csrf" -H "X-CSRF-Token: $csrf")
  fi
  if [ -n "$corpo" ]; then args+=(-d "$corpo"); fi
  curl "${args[@]}" "$API$rota"
}

# Login: guarda token e CSRF (linhas 1 e 2) a partir dos Set-Cookie.
entrar() {  # entrar <arquivo-de-sessão> <corpo>
  local status
  status=$(curl -sS -D "$TMP/cab" -o "$TMP/corpo" -w '%{http_code}' -X POST \
    -H 'Content-Type: application/json' -d "$2" "$API/api/auth/login")
  [ "$status" = 200 ] || { echo "login falhou ($status): $(cat "$TMP/corpo")"; return 1; }
  grep -i '^set-cookie: sinais_sessao=' "$TMP/cab" | sed -E 's/^[^=]*=([^;]*).*/\1/' | tr -d '\r' >"$1"
  grep -i '^set-cookie: sinais_csrf=' "$TMP/cab" | sed -E 's/^[^=]*=([^;]*).*/\1/' | tr -d '\r' >>"$1"
}

SENHA_ADMIN="fumaca-admin-$(date +%s)"
URI=$($COMPOSE exec -T -e SINAIS_ADMIN_SENHA="$SENHA_ADMIN" api \
  python -m sinais.processos.criar_admin --email admin@fumaca.local --nome Fumaca)
case "$URI" in otpauth://totp/*) echo "admin criado (URI TOTP emitida)";; *) echo "criar_admin falhou"; exit 1;; esac
SEGREDO=$(printf '%s' "$URI" | sed -E 's/.*secret=([A-Z2-7]+).*/\1/')
CODIGO=$($COMPOSE exec -T api python -c "import pyotp, sys; print(pyotp.TOTP(sys.argv[1]).now())" "$SEGREDO")

st=$(pedir POST /api/auth/login - '{"email":"admin@fumaca.local","senha":"'"$SENHA_ADMIN"'"}')
{ [ "$st" = 401 ] && grep -q totp_necessario "$TMP/corpo"; } || falha "admin sem TOTP deveria dar 401 ($st)"
echo "admin sem TOTP: 401 totp_necessario"
entrar "$TMP/admin" '{"email":"admin@fumaca.local","senha":"'"$SENHA_ADMIN"'","totp":"'"$CODIGO"'"}'
echo "admin entrou com 2FA"

st=$(pedir POST /api/admin/planos "$TMP/admin" '{"nome":"Fumaça","duracao_dias":30,"preco_centavos":0,"recursos":{"ativos":["BTCUSDT","ETHUSDT"],"expiracoes":["1m","5m","15m","30m","60m"],"modo_avancado":true,"cursos":false}}')
[ "$st" = 201 ] || falha "criar plano ($st)"
PLANO=$(jq -r .id "$TMP/corpo")
st=$(pedir POST /api/admin/usuarios "$TMP/admin" '{"email":"cliente@fumaca.local","nome":"Cliente","senha_temporaria":"cliente-fumaca-123","plano":'"$PLANO"'}')
[ "$st" = 201 ] || falha "criar cliente ($st)"
echo "plano $PLANO e cliente criados pelo admin"

entrar "$TMP/cliente" '{"email":"cliente@fumaca.local","senha":"cliente-fumaca-123"}'
st=$(pedir GET /api/eu "$TMP/cliente")
{ [ "$st" = 200 ] && [ "$(jq -r .assinatura.status "$TMP/corpo")" = ativa ]; } || falha "GET /api/eu ($st)"
echo "cliente: assinatura ativa"
st=$(pedir GET /api/admin/usuarios "$TMP/cliente")
[ "$st" = 403 ] || falha "cliente em rota de admin deveria dar 403 ($st)"
echo "cliente em rota de admin: 403"

st=$(pedir GET "/api/candles?simbolo=BTCUSDT&tg=1m&limite=5" "$TMP/cliente")
{ [ "$st" = 200 ] && [ "$(jq length "$TMP/corpo")" -gt 0 ]; } || falha "candles 1m ($st)"
echo "candles 1m: $(jq -c '.[-1]' "$TMP/corpo")"
st=$(pedir GET "/api/candles?simbolo=BTCUSDT&tg=5m&limite=3" "$TMP/cliente")
[ "$st" = 200 ] || falha "candles 5m ($st)"
echo "candles 5m: $(jq length "$TMP/corpo")"

# A análise sai no primeiro fechamento de 1m depois que o motor carregou a janela.
for i in $(seq 1 240); do
  st=$(pedir GET "/api/analise?simbolo=BTCUSDT" "$TMP/cliente")
  if [ "$st" = 200 ]; then break; fi
  sleep 1
done
[ "$st" = 200 ] || falha "análise indisponível ($st)"
echo "análise: t=$(jq .t "$TMP/corpo") preço=$(jq -r .preco "$TMP/corpo")"
jq -r '.resumo[]' "$TMP/corpo" | sed 's/^/  - /'

st=$(pedir GET "/api/sinais?simbolo=BTCUSDT" "$TMP/cliente")
{ [ "$st" = 200 ] && [ "$(jq '[.[] | select(.direcao == "AGUARDAR")] | length' "$TMP/corpo")" = 5 ]; } || falha "sinais ($st)"
echo "sinais: 5 expirações em AGUARDAR ($(jq -r '.[0].motivo' "$TMP/corpo"))"

st=$(pedir POST /api/auth/logout "$TMP/cliente")
[ "$st" = 204 ] || falha "logout ($st)"
st=$(pedir GET /api/eu "$TMP/cliente")
[ "$st" = 401 ] || falha "sessão deveria estar revogada ($st)"
echo "logout: sessão revogada"
echo "Fumaça da API OK"
