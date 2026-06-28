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

## Production/staging skeleton

`docker-compose.prod.yml` is the VPS-oriented starting point for a single-node deployment:

- PostgreSQL with a named volume and healthcheck;
- Redis with AOF persistence and healthcheck;
- FastAPI API container;
- Celery worker;
- Celery beat;
- Caddy serving the built frontend and reverse proxying `/api/*` plus `/health`;
- json-file log rotation for all services.

Create the server env file from the example:

```bash
cp deploy/prod.env.example deploy/prod.env
```

Replace all placeholder passwords/secrets before starting anything. Keep `POSTGRES_PASSWORD` and the password inside
`INFRA__DATABASE_URL` in sync.

Validate the compose file:

```bash
RETENTION_ENV_FILE=prod.env.example docker compose --env-file deploy/prod.env.example -f deploy/docker-compose.prod.yml config
```

Build images:

```bash
docker compose --env-file deploy/prod.env -f deploy/docker-compose.prod.yml build
```

Run migrations as a one-off tool service:

```bash
docker compose --env-file deploy/prod.env -f deploy/docker-compose.prod.yml --profile tools run --rm migrate
```

Start the stack:

```bash
docker compose --env-file deploy/prod.env -f deploy/docker-compose.prod.yml up -d api worker beat caddy
```

Check status and logs:

```bash
docker compose --env-file deploy/prod.env -f deploy/docker-compose.prod.yml ps
docker compose --env-file deploy/prod.env -f deploy/docker-compose.prod.yml logs -f api worker beat caddy
curl -i https://retention.myflowy.app/health
```

### Operations checks

Show recent failed notification deliveries:

```bash
deploy/ops/failed-notification-deliveries.sh 20
```

Run the minimal monitor once:

```bash
deploy/ops/monitor.sh
```

On the VPS, run it from cron every minute or every five minutes. To send alerts to Telegram, set
`ALERTS__TELEGRAM_BOT_TOKEN` and `ALERTS__TELEGRAM_CHAT_ID` in `deploy/prod.env`.

When Caddy is running on the VPS, include it in service checks:

```bash
EXPECTED_SERVICES="postgres redis api worker beat caddy" deploy/ops/monitor.sh
```
