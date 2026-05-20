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

### Messenger bots (optional)

```bash
# TELEGRAM_BOT_TOKEN in repo root .env
make bots-up
```

See [`../bots/README.md`](../bots/README.md). API must be running on the host (`make backend-run`) so bots can call `RETENTION_API_URL` (default `http://host.docker.internal:8000`).
