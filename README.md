# Retention Studio

Retention Studio - сервис для частных мастеров, которым нужно вести клиентов, расписание, записи, уведомления и базовую аналитику возврата клиентов. Проект состоит из FastAPI backend, React/Vite frontend, PostgreSQL, Redis и Celery worker/beat для фоновых задач.

## Структура

| Путь | Назначение |
|------|------------|
| `src/app` | FastAPI-приложение, доменные модели, use cases, repositories, Celery tasks |
| `frontend` | SPA на React, Vite, TanStack Query, React Router |
| `tests` | Backend unit/API tests |
| `deploy` | Dev Docker Compose для PostgreSQL, Redis, smtp4dev и optional bot sidecars |
| `bots` | Telegram bot sidecar для привязки messenger-каналов |
| `docs` | Текущие планы: аналитика, рефакторинг, тестовые данные, MVP readiness |
| `scripts` | Dev-скрипты, включая seed данных для аналитики |

## Быстрый старт

1. Установить зависимости backend:

```bash
make backend-install
```

2. Скопировать `.env.example` в `.env` и при необходимости поменять значения:

```bash
cp .env.example .env
```

3. Поднять dev-инфраструктуру и применить миграции:

```bash
make infra-up
make backend-migrate
```

4. Запустить backend:

```bash
make backend-run
```

5. Установить и запустить frontend:

```bash
make frontend-install
make frontend-run
```

По умолчанию:

- API: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- smtp4dev web UI: `http://localhost:5000`

## Фоновые задачи

Для обычного dev-режима Celery worker и beat запускаются отдельно:

```bash
make celery-worker
make celery-beat
```

Beat ставит периодические задачи, worker их выполняет. Сейчас фоновые задачи используются для:

- доставки email/in-app уведомлений;
- доставки messenger-уведомлений после привязки канала;
- автозавершения прошедших записей;
- password reset email через общий notification pipeline.

В тестах можно включать eager-режим через настройки Celery, но в dev/prod режиме лучше держать worker и beat отдельными процессами.

## Переменные окружения

Основные группы настроек находятся в `.env.example`:

- `INFRA__*` - PostgreSQL и Redis;
- `SECURITY__*` - secret key, публичный origin frontend, TTL токенов;
- `SESSION__*` - cookie-настройки;
- `CELERY__*` - broker/result backend и eager-режим;
- `SMTP__*` - SMTP-доставка;
- `NOTIFICATIONS__*` - режим доставки уведомлений и параметры reminder scan;
- `MESSENGER_BOTS__*` - internal secret и настройки bot sidecars;
- `BOOKING__*` - шаг сетки слотов и горизонт записи.

Для production обязательно заменить `SECURITY__SECRET_KEY`, включить secure cookies, выставить реальные `CORS_ORIGINS`/`SECURITY__FRONTEND_PUBLIC_ORIGIN`, настроить SMTP и секреты bot sidecars.

## Реализованный функционал

### Auth

- регистрация мастера и клиента;
- email verification;
- login/logout через server-side session cookie;
- CSRF token для mutating-запросов;
- password reset/change;
- rate limit на чувствительные auth endpoints.

### Кабинет мастера

- обзор с быстрыми переходами в клиентов, услуги и записи;
- профиль и настройки мастера;
- расписание по дням недели с окнами работы;
- CRUD услуг с ценой, длительностью, валютой и активностью;
- база клиентов, локальные клиенты и приглашения;
- карточка клиента с текущими/историческими записями и быстрым созданием записи для выбранного клиента;
- создание, перенос, отмена и подтверждение записей;
- фиксация посещений, неявок и комментариев к действиям;
- центр уведомлений;
- настройки уведомлений по темам и каналам;
- аналитика по выручке, визитам, клиентам, услугам, потерянной выручке, загрузке расписания и клиентам на возврат.

### Кабинет клиента

- обзор связанных мастеров и ближайших записей;
- карточки мастеров с контактами и быстрыми переходами;
- история визитов;
- самостоятельная запись к мастеру по доступным слотам;
- перенос и отмена записи с комментарием;
- профиль клиента;
- центр уведомлений и настройки уведомлений.

### Уведомления

| Событие | In-app | Email | Messenger |
|---------|--------|-------|-----------|
| Создание записи | Да | Да | При привязанном канале и включенной теме |
| Перенос записи | Да | Да | При привязанном канале и включенной теме |
| Отмена записи | Да | Да | При привязанном канале и включенной теме |
| Password reset | Да, без секретной ссылки | Да | Нет |

Привязка Telegram вынесена в optional bot sidecar. Email остается обязательным системным каналом для auth-сценариев и может использоваться для booking-уведомлений.

### Аналитика

Реализован endpoint `GET /api/master/analytics` и frontend-страница `/master/analytics`.

Поддерживаемые периоды:

- текущий месяц;
- последние 30 дней;
- прошлый месяц;
- custom `from`/`to` на уровне API.

Метрики:

- выручка по завершенным записям;
- средний чек;
- завершенные, отмененные и пропущенные записи;
- новые и повторные клиенты;
- потерянная выручка по отменам и неявкам;
- динамика выручки по дням;
- эффективность услуг;
- клиенты на возврат на текущий момент;
- загрузка расписания как `booked_minutes / available_minutes`.

Деньги считаются по snapshot-значениям записи и группируются по snapshot currency. UI показывает основную валюту мастера и умеет читать список money-значений из API.

## API

Все публичные маршруты имеют префикс `/api`.

Основные группы:

- `/api/auth/*`
- `/api/invitations/*`
- `/api/master/profile`
- `/api/master/schedule`
- `/api/master/clients`
- `/api/master/services`
- `/api/master/bookings`
- `/api/master/notifications`
- `/api/master/notification-settings`
- `/api/master/analytics`
- `/api/client/profile`
- `/api/client/masters`
- `/api/client/bookings`
- `/api/client/availability`
- `/api/client/notifications`
- `/api/client/notification-settings`
- `/api/internal/messenger/*`

Доменные ошибки постепенно приведены к контракту:

```json
{
  "code": "domain.error_code",
  "detail": "English fallback",
  "context": {}
}
```

`context` возвращается только для ошибок, где use case передал структурированные детали.

## Миграции

Alembic-конфиг находится в `alembic.ini`, версии - в `src/app/migrations/versions`.

Текущая цепочка:

- `20260519_initial_schema.py`
- `20260520_booking_statuses.py`
- `20260521_booking_attendance_confirmed.py`
- `20260523_master_contacts_client_alias.py`
- `20260524_booking_action_comments.py`
- `20260525_remove_viber.py`
- `20260526_client_timezone.py`

Применить миграции:

```bash
make backend-migrate
```

## Проверки

Backend:

```bash
make backend-lint
make backend-test
```

Frontend:

```bash
make frontend-lint
make frontend-test
make frontend-build
```

Общие команды:

```bash
make lint
make test
```

Для данных аналитики можно использовать seed-скрипт:

```bash
uv run python scripts/seed_test_data.py --dry-run
uv run python scripts/seed_test_data.py
```

Подробности: [`docs/test_data.md`](docs/test_data.md).

## Текущее состояние планов

- [`docs/analytics_plan.md`](docs/analytics_plan.md) - что уже реализовано в аналитике и что стоит делать следующими итерациями.
- [`docs/refactor_plan.md`](docs/refactor_plan.md) - технический журнал AppError/use-case рефакторинга и оставшийся cleanup.
- [`docs/mvp_readiness.md`](docs/mvp_readiness.md) - готовность проекта к первичной выкатке на тестовый сервер.

## Что логично дальше

Перед первичной выкаткой:

- подготовить production/staging окружение: домены, HTTPS, Postgres, Redis, worker, beat, миграции;
- настроить реальный SMTP и deliverability;
- пройти ручной smoke checklist по мастерскому и клиентскому кабинетам;
- добавить базовое логирование/мониторинг worker и API;
- проверить backup/restore для PostgreSQL.

После тестовой выкатки мастерам:

- reminders и reactivation-уведомления;
- расширение messenger/SMS каналов;
- публичная запись без приглашения;
- продвинутые срезы аналитики;
- E2E-тесты для критических пользовательских сценариев.
