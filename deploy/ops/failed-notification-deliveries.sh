#!/usr/bin/env sh
set -eu

LIMIT="${1:-20}"
COMPOSE_FILE="${COMPOSE_FILE:-deploy/docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-deploy/prod.env}"

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
fi

case "$LIMIT" in
  ''|*[!0-9]*)
    echo "Limit must be a positive integer" >&2
    exit 2
    ;;
esac

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T postgres \
  psql -U "${POSTGRES_USER:-retention}" -d "${POSTGRES_DB:-retention}" \
  -v "limit=$LIMIT" \
  -f /dev/stdin < deploy/ops/failed-notification-deliveries.sql
