Dev-only infrastructure backing the scheduling SaaS skeleton.

Requirements: Docker Compose v2 (`docker compose`).

```bash
docker compose -f deploy/docker-compose.dev.yml up -d
```

PostgreSQL listens on localhost `5432` with database `retention`, user/pass `retention`.
Redis listens on localhost `6379`.

Stop stacks with:

```bash
docker compose -f deploy/docker-compose.dev.yml down
```
