Ты senior full-stack engineer. Нужно создать начальное состояние нового проекта с нуля.

Проект: веб-приложение для мастеров услуг и их клиентов. Основной кейс: мастер ведет клиентов, услуги, расписание и записи; клиент получает инвайт-ссылку от мастера, выбирает услугу, видит доступные слоты с учетом длительности услуги и записывается. Telegram/Viber в будущем используются только как каналы уведомлений, а не как основной интерфейс.

Нужно сгенерировать production-minded, но не перегруженный стартовый skeleton проекта.

## Требуемый стек

Backend:
- Python 3.13+
- FastAPI
- SQLAlchemy 2 async
- PostgreSQL
- Alembic
- Redis
- Pydantic Settings
- pytest
- ruff
- uv

Frontend:
- React
- TypeScript
- Vite
- Tailwind CSS
- TanStack Query
- React Router
- React Hook Form
- Zod
- желательно shadcn/ui-compatible структура, но без необходимости сразу генерировать много UI-компонентов

Инфраструктура:
- Отдельная папка `deploy/`
- В `deploy/` разместить docker compose файлы для dev-инфраструктуры: PostgreSQL и Redis
- Backend и frontend пока можно запускать локально отдельно, без обязательного docker build
- Добавить `.env.example` для backend
- Добавить README с командами запуска
- Добавить `Makefile` в корень проекта с полезными dev-командами

## Продуктовая идея

Это не бот. Это SaaS/web app.

Пользовательский сценарий мастера:
- мастер регистрируется по email или username + password
- создает профиль мастера
- настраивает базовое расписание
- добавляет исключения по рабочим дням
- создает услуги с названием, описанием, длительностью и стоимостью
- добавляет клиентов вручную или отправляет им инвайт-ссылку
- видит календарь записей
- создает, переносит, отменяет записи

Пользовательский сценарий клиента:
- клиент получает инвайт-ссылку от мастера
- открывает публичную страницу мастера/инвайта
- выбирает услугу
- видит свободные слоты с учетом длительности выбранной услуги
- оставляет имя/телефон/email при необходимости
- создает запись
- в будущем может привязать Telegram/Viber/email для уведомлений

Важно: клиент может быть без полноценного аккаунта. Не нужно заставлять клиента регистрироваться на первом этапе.

## Основные доменные сущности

- `User`: обычный пользователь системы, авторизация по email или username + password
- `MasterProfile`: профиль мастера, принадлежит `User`
- `Service`: услуга мастера
  - `master_id`
  - `name`
  - `description`
  - `duration_min`
  - `price`
  - `currency`
  - `is_active`
  - `sort_order`
- `Client`: клиент мастера; может быть без собственного аккаунта
- `MasterClient`: связь мастера и клиента, может хранить alias, notes, invitation status
- `Invitation`: инвайт-ссылка от мастера клиенту, token, expiration, accepted_at
- `Schedule`: базовое расписание мастера
- `WorkdayOverride`: исключения по дням, выходной или измененные часы
- `Booking`: запись клиента к мастеру
  - обязательно должна ссылаться на `service_id`
  - должна хранить `start_at`, `end_at`, `duration_min`, `price_snapshot`, `currency_snapshot`
  - snapshot стоимости и длительности нужен, чтобы изменение услуги позже не ломало историю записей
- `NotificationChannel`: будущие каналы уведомлений: email, telegram, viber, sms
- `NotificationOutbox`: очередь уведомлений, пока можно только модель/заготовка

## Важная бизнес-логика

Свободные слоты должны считаться с учетом:
- базового расписания мастера
- исключений `WorkdayOverride`
- существующих записей
- длительности выбранной услуги
- таймзоны мастера

На первом этапе можно реализовать простой алгоритм:
- мастер задает рабочие дни, start_time, end_time, timezone
- услуга имеет `duration_min`
- API доступных слотов принимает `service_id` и дату/диапазон дат
- система возвращает слоты, в которые услуга целиком помещается
- пересечения с существующими booking запрещены

Не нужно делать сложные буферы между услугами, разные кабинеты/ресурсы, сотрудников, предоплату и recurring booking на первом шаге. Но архитектура должна позволять добавить это позже.

## Авторизация

- Сделать базовую backend-структуру для auth.
- Предпочтительно cookie/session-based auth или подготовить сервисный слой так, чтобы потом легко добавить HttpOnly cookie.
- На старте допустимо сделать простые endpoint'ы register/login/me/logout.
- Пароли хранить только в виде hash.
- Не использовать JWT в localStorage как основной рекомендуемый подход.
- Не привязывать пользователей к Telegram ID.

## Backend-структура

Структура должна быть примерно такой:

```text
backend/
  src/
    app/
      main.py
      api/
        deps.py
        router.py
        routes/
          auth.py
          masters.py
          services.py
          clients.py
          invitations.py
          bookings.py
          availability.py
      core/
        config.py
        security.py
        database.py
      models/
        user.py
        master.py
        service.py
        client.py
        invitation.py
        schedule.py
        booking.py
        notification.py
      schemas/
        auth.py
        user.py
        master.py
        service.py
        client.py
        invitation.py
        booking.py
        availability.py
      repositories/
        base.py
        users.py
        masters.py
        services.py
        clients.py
        invitations.py
        bookings.py
        schedules.py
      services/
        auth.py
        invitations.py
        bookings.py
        availability.py
        notifications.py
      use_cases/
        create_service.py
        create_invitation.py
        accept_invitation.py
        create_booking.py
        list_available_slots.py
      migrations/
        ...
    tests/
  pyproject.toml
  alembic.ini
  .env.example
```

Бизнес-логику не писать прямо в FastAPI route handlers. Route handlers должны вызывать services/use_cases.

## Минимально ожидаемые backend endpoints

Общее:
- `GET /health`

Auth:
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/logout`

Master:
- `GET /api/masters/me`
- `PUT /api/masters/me`

Services:
- `GET /api/services`
- `POST /api/services`
- `GET /api/services/{service_id}`
- `PUT /api/services/{service_id}`
- `DELETE /api/services/{service_id}` или soft-delete через `is_active=false`

Clients:
- `GET /api/clients`
- `POST /api/clients`

Invitations:
- `POST /api/invitations`
- `GET /api/invitations/{token}`
- `POST /api/invitations/{token}/accept`

Availability:
- `GET /api/availability?master_id=...&service_id=...&date=...`
- либо похожий endpoint, который возвращает доступные слоты для выбранной услуги

Bookings:
- `GET /api/bookings`
- `POST /api/bookings`
- `POST /api/bookings/{booking_id}/cancel`
- можно добавить `POST /api/bookings/{booking_id}/reschedule`, если это не сильно раздувает первый шаг

## Frontend-структура

Структура должна быть примерно такой:

```text
frontend/
  src/
    app/
      router.tsx
      providers.tsx
    api/
      client.ts
      auth.ts
      masters.ts
      services.ts
      clients.ts
      invitations.ts
      bookings.ts
      availability.ts
    pages/
      LoginPage.tsx
      RegisterPage.tsx
      DashboardPage.tsx
      ServicesPage.tsx
      ClientsPage.tsx
      SchedulePage.tsx
      BookingsPage.tsx
      InvitationPage.tsx
    components/
      layout/
      ui/
      services/
      bookings/
    lib/
      forms.ts
      query.ts
      validators.ts
  package.json
  vite.config.ts
  tailwind.config.js
```

## Минимально ожидаемые frontend страницы

- login
- register
- dashboard
- services: список услуг, создание/редактирование услуги
- clients
- bookings
- schedule
- invitation landing page по token

Для страницы инвайта:
- показать мастера
- показать список активных услуг
- после выбора услуги показать доступные слоты
- дать создать запись

## Папка deploy

Создать:

```text
deploy/
  docker-compose.dev.yml
  README.md
```

`docker-compose.dev.yml` должен поднимать:
- postgres
- redis

Backend и frontend не обязательно контейнеризировать на первом шаге.

## Makefile

В корне проекта нужен `Makefile` с командами:

- `make infra-up` - поднять PostgreSQL и Redis через `deploy/docker-compose.dev.yml`
- `make infra-down` - остановить dev-инфраструктуру
- `make backend-install` - установить backend зависимости через `uv sync`
- `make backend-migrate` - применить Alembic migrations
- `make backend-run` - запустить FastAPI dev server
- `make backend-test` - запустить pytest
- `make backend-lint` - запустить ruff
- `make frontend-install` - установить frontend зависимости
- `make frontend-run` - запустить Vite dev server
- `make frontend-build` - собрать frontend
- `make test` - запустить backend tests и frontend checks, если они есть
- `make lint` - запустить backend/frontend lint, если настроены

Команды должны быть реалистичными и соответствовать созданной структуре.

Желательные команды внутри Makefile:

```makefile
infra-up:
	docker compose -f deploy/docker-compose.dev.yml up -d

infra-down:
	docker compose -f deploy/docker-compose.dev.yml down

backend-run:
	cd backend && uv run uvicorn app.main:app --reload

frontend-run:
	cd frontend && npm run dev
```

## Качество и ограничения

- Код должен быть типизирован.
- Добавить ruff config.
- Добавить понятные имена модулей.
- Не делать огромные файлы.
- SQLAlchemy models и Pydantic schemas держать отдельно.
- Использовать async DB session.
- Сделать Alembic initial migration.
- Добавить базовые тесты хотя бы для health/auth/service-level smoke tests.
- Не добавлять лишнюю сложность вроде Kubernetes, Celery, OAuth, платежей, Prometheus на первом шаге.
- Но архитектура должна позволять добавить уведомления Telegram/Viber позже через provider/adapters.

## Уведомления

Домен: `NotificationDispatcher` пишет событие, `UserNotification`, `NotificationDelivery`; воркер или eager-режим
доставляют по каналу. Для email верификации — шаблоны + SMTP в `registration_mail` (`deliver_email_verification`).
Другие каналы (Telegram/Viber/SMS) логично добавлять отдельными модулями-адаптерами и хэндлерами в воркере,
не смешивая транспорт с use-case.

## README

Добавить README с:
- кратким описанием проекта
- описанием структуры
- требованиями
- запуском dev-инфраструктуры через `make infra-up`
- запуском backend
- запуском frontend
- запуском тестов
- применением миграций

## В конце работы выведи

1. Краткое описание созданной структуры.
2. Команды запуска dev-инфраструктуры.
3. Команды запуска backend.
4. Команды запуска frontend.
5. Что уже реализовано.
6. Что логично делать следующим шагом.
