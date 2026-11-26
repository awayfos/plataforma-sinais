#!/usr/bin/env bash
# Backend local da Plataforma Sinais pelo Docker Compose (passo a passo em docs/COMO-RODAR-LOCAL.md).
#
#   infra/dev.sh subir              cria o .env (se faltar), sobe tudo e espera a API responder
#   infra/dev.sh admin EMAIL [NOME] cria/redefine o admin e mostra a URI do autenticador (2FA)
#   infra/dev.sh status             estado dos serviços e quantos candles já foram baixados
#   infra/dev.sh logs [SERVIÇO]     acompanha os logs (Ctrl+C para sair)
#   infra/dev.sh parar              para os serviços (os dados ficam)
#   infra/dev.sh apagar             para e APAGA os dados do banco (recomeça do zero)
#
# Variáveis: ENV_FILE (padrão .env), SINAIS_ADMIN_SENHA (senha do admin sem perguntar no terminal),
# SINAIS_DEV_DIAS (dias de histórico de 1 min no .env novo; padrão 3).
set -euo pipefail
cd "$(dirname "$0")/.."
ENV_FILE=${ENV_FILE:-.env}
COMPOSE=(docker compose -f infra/docker-compose.yml --env-file "$ENV_FILE")
API=http://127.0.0.1:8000

erro() { echo "ERRO: $*" >&2; exit 1; }

exigir_docker() {
  command -v docker >/dev/null 2>&1 || erro "Docker não encontrado. Instale o Docker (ver docs/COMO-RODAR-LOCAL.md)."
  docker compose version >/dev/null 2>&1 || erro "Docker Compose v2 não encontrado ('docker compose')."
  docker info >/dev/null 2>&1 || erro "O Docker não está rodando (abra o Docker Desktop ou inicie o serviço)."
}

criar_env() {
  [ -f "$ENV_FILE" ] && return
  echo "Criando $ENV_FILE a partir do .env.example (só para desenvolvimento)…"
  cp .env.example "$ENV_FILE"
  # Desenvolvimento: pouco histórico para a primeira carga terminar em minutos, não em horas.
  sed -i.bak "s#^SINAIS_HISTORICO_DIAS=.*#SINAIS_HISTORICO_DIAS=${SINAIS_DEV_DIAS:-3}#" "$ENV_FILE"
  sed -i.bak "s#^SINAIS_HISTORICO_DIAS_1S=.*#SINAIS_HISTORICO_DIAS_1S=1#" "$ENV_FILE"
  rm -f "$ENV_FILE.bak"
}

subir() {
  exigir_docker
  criar_env
  "${COMPOSE[@]}" up -d --build
  echo "Esperando a API em $API (até 5 min; a primeira vez constrói as imagens)…"
  for _ in $(seq 1 300); do
    if curl -fsS "$API/api/publico/estatisticas" >/dev/null 2>&1; then
      echo "API no ar."
      status
      cat <<'TEXTO'

Próximos passos:
  1. Admin com 2FA:      infra/dev.sh admin voce@exemplo.com "Seu Nome"
  2. Frontend:           cd frontend && npm ci && npm run dev
  3. Abra no navegador:  http://localhost:3000   (use "localhost", não 127.0.0.1)
O histórico continua baixando em segundo plano: acompanhe com "infra/dev.sh logs coletor".
TEXTO
      return
    fi
    sleep 1
  done
  "${COMPOSE[@]}" logs --tail=80 api migracoes
  erro "a API não respondeu em 5 minutos (logs acima)."
}

admin() {
  local email=${1:-} nome=${2:-Administrador}
  [ -n "$email" ] || erro "uso: infra/dev.sh admin EMAIL [NOME]"
  exigir_docker
  echo "Senha do admin: mínimo de 10 caracteres."
  if [ -n "${SINAIS_ADMIN_SENHA:-}" ]; then
    "${COMPOSE[@]}" exec -T -e SINAIS_ADMIN_SENHA api \
      python -m sinais.processos.criar_admin --email "$email" --nome "$nome"
  else
    "${COMPOSE[@]}" exec api python -m sinais.processos.criar_admin --email "$email" --nome "$nome"
  fi
  cat <<'TEXTO'

A linha otpauth://… acima é o segredo do 2FA. No aplicativo autenticador (Google Authenticator,
Microsoft Authenticator, Authy, 1Password…), escolha "adicionar conta" → "inserir chave" e cole o valor de
secret=… (ou gere um QR code com a linha inteira). Não compartilhe essa linha.
TEXTO
}

status() {
  "${COMPOSE[@]}" ps
  local m1
  m1=$("${COMPOSE[@]}" exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT count(*) FROM candles_1m"' 2>/dev/null || echo "?")
  echo "candles de 1 min no banco: ${m1//[[:space:]]/}"
}

case "${1:-subir}" in
  subir) subir ;;
  admin) shift; admin "$@" ;;
  status) exigir_docker; status ;;
  logs) exigir_docker; shift; "${COMPOSE[@]}" logs -f --tail=100 "$@" ;;
  parar) exigir_docker; "${COMPOSE[@]}" stop ;;
  apagar) exigir_docker; "${COMPOSE[@]}" down -v ;;
  *) sed -n '2,13p' "$0"; exit 1 ;;
esac
