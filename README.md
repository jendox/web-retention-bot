# Retention Studio

Веб‑SaaS для мастеров услуг и их клиентов: профиль, расписание, услуги, клиентская база, инвайты, свободные слоты, записи и уведомления (in‑app + email). Изначальная постановка — в [`docs/retention_bot_prompt.md`](docs/retention_bot_prompt.md).

## Структура репозитория

| Путь | Назначение |
|------|------------|
| `src/app/` | Backend: FastAPI, доменные модели, use cases, Alembic |
| `tests/` | Pytest (API, use cases, уведомления) |
| `frontend/` | SPA: React 19, TypeScript, Vite, Tailwind 4, TanStack Query |
| `deploy/` | Dev‑инфра: PostgreSQL, Redis, [smtp4dev](https://github.com/rnwood/smtp4dev) |
| `docs/` | Продуктовый промпт и заметки |

Корень: `pyproject.toml`, `alembic.ini`, `.env.example`, `Makefile`.

## Требования

- Python **3.13+**, [uv](https://docs.astral.sh/uv/)
- Node **20+**, npm
- Docker Compose v2 (`docker compose`)

## Быстрый старт (локально)

### 1. Инфраструктура

```bash
make infra-up      # Postgres :5432, Redis :6379, smtp4dev :25 / UI :5000
make infra-down
make infra-clean   # с удалением volumes (чистая БД)
```

Строка подключения по умолчанию: `postgresql+asyncpg://retention:retention@localhost:5432/retention`.

### 2. Backend

```bash
make backend-install
cp .env.example .env   # при необходимости поправьте URL и SMTP
make backend-migrate
make backend-run       # http://127.0.0.1:8000 — /health, /docs, /api/*
```

Сессии: HttpOnly cookie `session_id`, opaque id в Redis (`src/app/services/sessions.py`). Для мутаций — CSRF (`X-CSRF-Token`).

### 3. Фоновые задачи (опционально, для email и автозавершения записей)

В двух терминалах (при `CELERY__TASK_ALWAYS_EAGER=false`):

```bash
make celery-worker
make celery-beat     # периодически завершает прошедшие SCHEDULED → COMPLETED
```

Для тестов и части сценариев dev без воркера: `NOTIFICATIONS__EAGER_DELIVERIES=true` в `.env` — письма по записям отправляются синхронно в процессе API (см. `tests/conftest.py`).

Письма в dev: SMTP на `127.0.0.1:25` (smtp4dev), веб‑интерфейс — http://localhost:5000.

### 4. Frontend

```bash
make frontend-install
make frontend-run      # http://127.0.0.1:5173 — proxy /api → :8000
```

Отдельный хостинг SPA: `VITE_API_BASE_URL` (`frontend/.env.example`).

## Makefile

| Цель | Описание |
|------|----------|
| `make infra-up` / `infra-down` / `infra-clean` | Docker Compose dev stack |
| `make backend-install` | `uv sync` |
| `make backend-migrate` | Alembic `upgrade head` |
| `make backend-run` | Uvicorn с reload |
| `make celery-worker` / `celery-beat` | Очередь и периодика |
| `make backend-test` / `backend-lint` | pytest, ruff |
| `make frontend-install` / `frontend-run` / `frontend-build` / `frontend-lint` | npm |
| `make test` | pytest + ESLint frontend |
| `make lint` | ruff + ESLint |

## Переменные окружения

См. [`.env.example`](.env.example). Основные группы (префикс `SECTION__`):

- **INFRA** — Postgres, Redis
- **SECURITY** — `SECRET_KEY`, `FRONTEND_PUBLIC_ORIGIN`, верификация email
- **SESSION** — cookie, TTL
- **CELERY** — broker, `TASK_ALWAYS_EAGER`
- **SMTP** — исходящая почта
- **BOOKING** — шаг слотов, горизонт записи, интервал автозавершения
- **NOTIFICATIONS** — `EAGER_DELIVERIES` (синхронная доставка email без Celery)

## Реализованный функционал

### Аутентификация и роли

- Регистрация / вход / выход, подтверждение email (ссылка на SPA `/verify-email`)
- Пользователь может быть мастером (`MasterProfile`) и/или клиентом (`Client` + связи `MasterClient`)
- Инвайты по токену (`/invite/:token`), привязка клиента к мастеру

### Кабинет мастера (UI + API)

- Дашборд, **расписание** (недельные правила и исключения), **услуги**, **клиенты** (карточка, alias, заметки)
- **Записи**: создание, список (upcoming/history), отмена и перенос с опциональным комментарием для клиента
- Подтверждение явки (attended / no‑show) для завершённых визитов
- **Настройки**: контакты мастера (email, телефон, Telegram, Viber), публичное имя
- Страница **уведомлений** (in‑app лента, отметка прочитанным)

### Кабинет клиента (UI + API)

- Обзор, **мои мастера** (список, alias мастера в кабинете), **визиты** (предстоящие и история)
- Самостоятельная запись на свободный слот, отмена и перенос с опциональным комментарием для мастера
- Отображение комментариев к отмене/переносу в списке визитов

### Уведомления

Центральный диспетчер: событие → `UserNotification` (in‑app) + `NotificationDelivery` (каналы).

| Событие | Кому | Каналы |
|---------|------|--------|
| Подтверждение email | пользователь | email (+ in‑app копия) |
| Мастер создал запись | клиент (связан, email подтверждён) | in‑app + email |
| Мастер отменил / перенёс | клиент | in‑app + email (с комментарием, если есть) |
| Клиент создал / отменил / перенёс | мастер (email подтверждён) | in‑app + email (с комментарием, если есть) |

Шаблоны писем: `src/app/services/notifications/templates/email/`. Отдельные тексты для аудитории master/client.

Заготовки в модели (без полной продуктовой логики): напоминания перед визитом, re‑engagement, Telegram/Viber/SMS в enum каналов.

### Записи и слоты

- Статусы: `SCHEDULED`, `COMPLETED`, `NO_SHOW`, `CANCELLED`
- Availability по дню и услуге с учётом расписания, исключений и занятых слотов
- Поля на записи: `cancel_comment`, `reschedule_comment` (до 500 символов)

## Миграции БД

```bash
make backend-migrate
```

Версии в `src/app/migrations/versions/`:

1. `20260519_initial_schema` — пользователи, мастера, клиенты, услуги, расписание, записи, уведомления
2. `20260520_booking_statuses`
3. `20260521_booking_attendance_confirmed`
4. `20260523_master_contacts_client_alias`
5. `20260524_booking_action_comments`

После смены схемы на существующей dev‑БД удобно: `make infra-clean && make backend-migrate`.

## API (кратко)

Префикс `/api`, OpenAPI: http://127.0.0.1:8000/docs

- `/api/auth/*` — register, login, logout, me, verify-email
- `/api/masters/me` — профиль, расписание
- `/api/services/*`, `/api/clients/*`, `/api/invitations/*`
- `/api/availability` — свободные слоты
- `/api/bookings` — CRUD записей мастера; `/api/bookings/me` — кабинет клиента
- `/api/notifications/me` — in‑app лента

## Тесты и качество

```bash
make test
make lint
```

Backend: pytest + httpx, aiosqlite в тестах; ruff. Frontend: ESLint, `tsc -b` при `frontend-build`.

## Что логично дальше

- Настройки каналов уведомлений (отключение email и др., кроме in‑app) — UI частично заглушка
- Напоминания перед визитом и retention‑цепочки (модели есть, доставка не завершена)
- Telegram / Viber / SMS как каналы
- Расширение прав и границ «кто может что» между мастером и клиентом
- Оплата, буферы между записями, публичная страница записи без инвайта

## Деплой

Prod‑манифесты пока минимальны; dev‑стек описан в [`deploy/README.md`](deploy/README.md).
