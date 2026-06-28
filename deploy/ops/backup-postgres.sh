#!/usr/bin/env sh
set -eu

COMPOSE_FILE="${COMPOSE_FILE:-deploy/docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-deploy/prod.env}"
BACKUP_DIR="${BACKUP_DIR:-deploy/backups/postgres}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
fi

POSTGRES_USER="${POSTGRES_USER:-retention}"
POSTGRES_DB="${POSTGRES_DB:-retention}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_file="${BACKUP_DIR}/${POSTGRES_DB}-${timestamp}.dump"
tmp_file="${backup_file}.tmp"

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

case "$BACKUP_RETENTION_DAYS" in
  ''|*[!0-9]*)
    echo "BACKUP_RETENTION_DAYS must be a non-negative integer" >&2
    exit 2
    ;;
esac

mkdir -p "$BACKUP_DIR"

if ! compose ps --status running --services | grep -qx postgres; then
  echo "PostgreSQL service is not running" >&2
  exit 1
fi

echo "Creating PostgreSQL backup: $backup_file"
compose exec -T postgres pg_dump \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  --format=custom \
  --no-owner \
  --no-privileges \
  > "$tmp_file"

if [ ! -s "$tmp_file" ]; then
  rm -f "$tmp_file"
  echo "Backup file is empty" >&2
  exit 1
fi

mv "$tmp_file" "$backup_file"

if [ "$BACKUP_RETENTION_DAYS" -gt 0 ]; then
  find "$BACKUP_DIR" -type f -name "${POSTGRES_DB}-*.dump" -mtime +"$BACKUP_RETENTION_DAYS" -delete
fi

echo "Backup complete: $backup_file"
