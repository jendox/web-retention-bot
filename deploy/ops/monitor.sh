#!/usr/bin/env sh
set -eu

COMPOSE_FILE="${COMPOSE_FILE:-deploy/docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-deploy/prod.env}"
EXPECTED_SERVICES="${EXPECTED_SERVICES:-postgres redis api worker beat}"
FAILED_DELIVERIES_THRESHOLD="${FAILED_DELIVERIES_THRESHOLD:-0}"

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
fi

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

failures=""

add_failure() {
  failures="${failures}
- $1"
}

for service in $EXPECTED_SERVICES; do
  if ! compose ps --status running --services | grep -qx "$service"; then
    add_failure "service '$service' is not running"
  fi
done

if ! compose exec -T api python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()" >/dev/null 2>&1; then
  add_failure "api /health failed inside container"
fi

if ! compose exec -T worker celery -A app.worker.celery_app inspect ping >/dev/null 2>&1; then
  add_failure "celery worker ping failed"
fi

failed_deliveries="$(
  compose exec -T postgres psql -U "${POSTGRES_USER:-retention}" -d "${POSTGRES_DB:-retention}" -tA \
    -c "SELECT count(*) FROM notification_deliveries WHERE status = 'failed';" 2>/dev/null \
    || echo "unknown"
)"

case "$failed_deliveries" in
  ''|*[!0-9]*)
    add_failure "failed notification deliveries count query failed"
    ;;
  *)
    if [ "$failed_deliveries" -gt "$FAILED_DELIVERIES_THRESHOLD" ]; then
      add_failure "failed notification deliveries: $failed_deliveries"
    fi
    ;;
esac

if [ -z "$failures" ]; then
  echo "OK: services, api health, celery ping, failed deliveries"
  exit 0
fi

message="Retention alert on ${APP_DOMAIN:-unknown-domain}:${failures}"
echo "$message" >&2

if [ -n "${ALERTS__TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${ALERTS__TELEGRAM_CHAT_ID:-}" ]; then
  curl -fsS \
    -X POST "https://api.telegram.org/bot${ALERTS__TELEGRAM_BOT_TOKEN}/sendMessage" \
    --data-urlencode "chat_id=${ALERTS__TELEGRAM_CHAT_ID}" \
    --data-urlencode "text=${message}" \
    >/dev/null
fi

exit 1
