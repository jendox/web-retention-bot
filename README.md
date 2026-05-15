# Retention Studio (skeleton)

Веб‑SaaS для мастеров и клиентов: услуги, расписание, инвайты, свободные слоты и записи. Стек и изначальная идея заданы промптом в `docs/retention_bot_prompt.md`.

## Структура

- **Корень репозитория** — backend: `src/app/` (FastAPI), `tests/`, `alembic.ini`, `pyproject.toml`, `.env.example`.
- `frontend/` — React + TS + Vite + Tailwind 4 + TanStack Query + RHF/Zod + React Router.
- `deploy/` — dev‑инфраструктура: PostgreSQL + Redis (`deploy/docker-compose.dev.yml`).

## Требования

- Python 3.13+, `uv`.
- Node 20+ и `npm`.
- Docker (для `make infra-up`).

## Dev‑инфраструктура

```bash
make infra-up          # Postgres :5432, Redis :6379
make infra-down
```

PostgreSQL (по умолчанию): `postgresql://retention:retention@localhost:5432/retention`.

## Backend (из корня репозитория)

```bash
make backend-install
cp .env.example .env   # или отредактируйте DATABASE_URL / REDIS_URL
make backend-migrate
make backend-run       # http://127.0.0.1:8000 — health /docs /api/*
make backend-test
make backend-lint
```

Сессии: HttpOnly‑cookie (`session_id`) + opaque id в Redis (см. `src/app/services/sessions.py`).

## Frontend

```bash
make frontend-install
make frontend-run      # http://127.0.0.1:5173 — Vite proxy /api → :8000
make frontend-build
make frontend-lint
```

При отдельном хостинге задайте `VITE_API_BASE_URL` (`frontend/.env.example`).

## Агрегированные цели Makefile

```bash
make test   # pytest + ESLint frontend
make lint   # ruff + ESLint
```

## Что уже есть

- Health, auth cookie‑session (register/login/me/logout), CRUD профиля и расписания мастера, услуги, клиенты, инвайты, availability, записи (+ cancel/reschedule), порт заглушек уведомлений.
- Initial Alembic migration в `src/app/migrations/versions/`.

## Что логично дальше

- Роли/прав доступа и полный UI расписания/исключений.
- Связка outbox ↔ провайдеры email/Telegram/Viber по очереди.
- Валидация переносов, буферы, оплата, аккаунт клиента и каналы напоминаний.
