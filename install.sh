#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="${ROOT_DIR}/deploy"
ENV_FILE="${DEPLOY_DIR}/.env.production"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Ошибка: не найдена команда '$1'."
    exit 1
  fi
}

prompt_default() {
  local label="$1"
  local default_value="$2"
  local value
  read -r -p "${label} [${default_value}]: " value
  if [[ -z "${value}" ]]; then
    value="${default_value}"
  fi
  printf '%s' "${value}"
}

prompt_required() {
  local label="$1"
  local value
  while true; do
    read -r -p "${label}: " value
    if [[ -n "${value}" ]]; then
      printf '%s' "${value}"
      return
    fi
    echo "Значение обязательно."
  done
}

prompt_secret() {
  local label="$1"
  local value
  while true; do
    read -r -s -p "${label}: " value
    echo
    if [[ -n "${value}" ]]; then
      printf '%s' "${value}"
      return
    fi
    echo "Значение обязательно."
  done
}

echo "Установка wb-sync-service"
echo

require_command docker
if ! docker compose version >/dev/null 2>&1; then
  echo "Ошибка: не найден Docker Compose plugin."
  exit 1
fi

mkdir -p "${DEPLOY_DIR}"

DB_HOST="$(prompt_required 'PostgreSQL host')"
DB_PORT="$(prompt_default 'PostgreSQL port' '5432')"
DB_NAME="$(prompt_required 'PostgreSQL database')"
DB_USER="$(prompt_required 'PostgreSQL user')"
DB_PASSWORD="$(prompt_secret 'PostgreSQL password')"
DB_SCHEMA="$(prompt_default 'PostgreSQL schema' 'wb_prod')"
POLL_SECONDS="$(prompt_default 'Интервал перечитывания конфигурации, сек' '10')"
HTTP_TIMEOUT="$(prompt_default 'HTTP timeout, сек' '60')"
RETRY_ATTEMPTS="$(prompt_default 'Количество retry' '5')"
RETRY_BASE="$(prompt_default 'Базовая пауза retry, сек' '2')"
RATE_LIMIT="$(prompt_default 'Rate limit на аккаунт, сек' '60')"
LOG_LEVEL="$(prompt_default 'Log level' 'INFO')"

cat > "${ENV_FILE}" <<EOF
WB_SYNC_PG_HOST=${DB_HOST}
WB_SYNC_PG_PORT=${DB_PORT}
WB_SYNC_PG_DATABASE=${DB_NAME}
WB_SYNC_PG_USER=${DB_USER}
WB_SYNC_PG_PASSWORD=${DB_PASSWORD}
WB_SYNC_DB_SCHEMA=${DB_SCHEMA}
WB_SYNC_DISPATCHER_POLL_SECONDS=${POLL_SECONDS}
WB_SYNC_HTTP_TIMEOUT_SECONDS=${HTTP_TIMEOUT}
WB_SYNC_RETRY_ATTEMPTS=${RETRY_ATTEMPTS}
WB_SYNC_RETRY_BASE_SECONDS=${RETRY_BASE}
WB_SYNC_RATE_LIMIT_SECONDS=${RATE_LIMIT}
WB_SYNC_LOG_LEVEL=${LOG_LEVEL}
EOF

echo
echo "Сборка контейнера..."
docker compose build wb-sync

echo
echo "Проверка подключения к PostgreSQL и bootstrap схемы..."
docker compose run --rm wb-sync init-db

echo
echo "Запуск сервиса..."
docker compose up -d wb-sync

echo
if docker compose ps --status running | grep -q "wb-sync"; then
  echo "Установка завершена успешно."
  echo "Сервис запущен."
  echo "Production-схема: ${DB_SCHEMA}"
  echo "Файл конфигурации: ${ENV_FILE}"
else
  echo "Ошибка: контейнер не запущен."
  docker compose ps
  exit 1
fi
