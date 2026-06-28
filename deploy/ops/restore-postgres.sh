#!/usr/bin/env sh
set -eu

COMPOSE_FILE="${COMPOSE_FILE:-deploy/docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-deploy/prod.env}"

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 path/to/backup.dump" >&2
  exit 2
fi

backup_file="$1"

if [ ! -f "$backup_file" ]; then
  echo "Backup file not found: $backup_file" >&2
  exit 2
fi

if [ ! -s "$backup_file" ]; then
  echo "Backup file is empty: $backup_file" >&2
  exit 2
fi

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
fi

POSTGRES_USER="${POSTGRES_USER:-retention}"
POSTGRES_DB="${POSTGRES_DB:-retention}"
required_confirmation="restore ${POSTGRES_DB}"

if [ "${RESTORE_CONFIRM:-}" != "$required_confirmation" ]; then
  echo "Refusing to restore without explicit confirmation." >&2
  echo "This will replace objects in database '$POSTGRES_DB'." >&2
  echo "Run with: RESTORE_CONFIRM='$required_confirmation' $0 $backup_file" >&2
  exit 2
fi

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

if ! compose ps --status running --services | grep -qx postgres; then
  echo "PostgreSQL service is not running" >&2
  exit 1
fi

echo "Restoring PostgreSQL backup into database '$POSTGRES_DB': $backup_file"
compose exec -T postgres pg_restore \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges \
  < "$backup_file"

echo "Restore complete."
