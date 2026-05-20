Dev-only infrastructure for Retention Studio.

Requirements: Docker Compose v2 (`docker compose`). From the repo root:

```bash
make infra-up
# or: docker compose -f deploy/docker-compose.dev.yml up -d
```

| Service | Ports | Notes |
|---------|-------|--------|
| PostgreSQL | `5432` | DB `retention`, user/pass `retention` |
| Redis | `6379` | sessions + Celery broker (DB 0/1 in `.env`) |
| smtp4dev | `25` (SMTP), `5000` (web UI) | Catch-all dev mailbox; matches default `SMTP__*` in `.env.example` |

Stop: `make infra-down`. Reset data: `make infra-clean`.
