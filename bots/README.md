# Messenger bot sidecars

Отдельные лёгкие сервисы для Telegram и Viber. **Не импортируют** код основного приложения (`src/app`) — только доставку уведомлений через Bot API и вызов internal API Retention.

Роль каналов: **только push-уведомления** (текст + ссылка в приложение). Запись, настройки и привязка каналов — в веб-кабинете.

## Структура (uv workspace)

Пакеты объявлены в корневом `pyproject.toml`:

```toml
[tool.uv.workspace]
members = ["bots/shared", "bots/telegram", "bots/viber"]
```

| Путь | Пакет | Назначение |
|------|-------|------------|
| `bots/shared/` | `retention-messenger-shared` | HTTP-клиент к API (`retention_shared.api`) |
| `bots/telegram/` | `retention-telegram-bot` | Telegram sidecar |
| `bots/viber/` | `retention-viber-bot` | Viber sidecar (заготовка) |

Зависимость между workspace-пакетами в `bots/telegram/pyproject.toml` и `bots/viber/pyproject.toml`:

```toml
[tool.uv.sources]
retention-messenger-shared = { workspace = true }
```

## Архитектура привязки Telegram

```text
Настройки SPA → POST .../channels/telegram/link
    → Redis: messenger:link:telegram:{token} → user_id (TTL 15 мин)
    → connect_url: https://t.me/retention_studio_bot?start={token}

Пользователь → Start в боте
    → telegram-bot (polling в dev / webhook в prod)
    → POST /api/internal/messenger/telegram/complete-link
        (X-Bot-Secret, token, external_id = chat_id)
    → API: notification_channels.address = chat_id

Отправка (из API, когда подключено в dispatcher)
    → POST http://telegram-bot:8091/v1/send { external_id, text }
    → Telegram Bot API sendMessage
```

## Переменные окружения

### В `.env` корня (API + compose)

```env
TELEGRAM_BOT_TOKEN=...                    # только для контейнера/процесса бота
MESSENGER_BOTS__INTERNAL_SECRET=...       # общий секрет API ↔ sidecar
MESSENGER_BOTS__TELEGRAM_BOT_USERNAME=retention_studio_bot
# MESSENGER_BOTS__TELEGRAM_SERVICE_URL=http://localhost:8091  # когда API шлёт в бота
```

### В процессе бота (локально или Docker)

| Переменная | Описание |
|------------|----------|
| `TELEGRAM_BOT_TOKEN` | Токен от [@BotFather](https://t.me/BotFather) |
| `BOT_INTERNAL_SECRET` | То же, что `MESSENGER_BOTS__INTERNAL_SECRET` |
| `RETENTION_API_URL` | URL API: `http://127.0.0.1:8000` (локально) или `http://host.docker.internal:8000` (Docker → хост) |
| `TELEGRAM_MODE` | `polling` (dev) или `webhook` (prod) |

Порты sidecar: **8091** (Telegram), **8092** (Viber) — health, `/v1/send`, webhook.

## Локальная разработка (uv + один `.venv` в корне)

```bash
# из корня репозитория
uv sync

make infra-up          # Redis (токены привязки), Postgres
make backend-run     # API :8000
make frontend-run    # SPA :5173 (опционально)
```

Запуск Telegram-бота:

```bash
export TELEGRAM_BOT_TOKEN='...'
export BOT_INTERNAL_SECRET='dev-bot-internal-secret-change-me'
export RETENTION_API_URL='http://127.0.0.1:8000'
export TELEGRAM_MODE='polling'

uv run --directory bots/telegram \
  uvicorn app.main:app --host 127.0.0.1 --port 8091 --reload
```

Проверка: `curl http://127.0.0.1:8091/health`

**Не запускайте одновременно** локальный polling и `make bots-up` — на один токен Bot API допускает одного poller.

### PyCharm

1. Интерпретатор: корневой `.venv` (после `uv sync`).
2. Run Configuration:
   - **Module:** `uvicorn`
   - **Parameters:** `app.main:app --host 127.0.0.1 --port 8091 --reload`
   - **Working directory:** `bots/telegram`
   - **Environment:** `TELEGRAM_BOT_TOKEN`, `BOT_INTERNAL_SECRET`, `RETENTION_API_URL=http://127.0.0.1:8000`, `TELEGRAM_MODE=polling`
3. Backend — отдельная конфигурация с `--app-dir src`.

Breakpoints: `bots/telegram/app/handlers.py`, `app/main.py`.

## Docker (лёгкий образ)

Сборка из `deploy/docker-compose.bots.yml`, context `bots/`. Dockerfile ставит только `retention-messenger-shared` и пакет бота — без FastAPI/SQLAlchemy.

```bash
# API на хосте
make backend-run

# бот в контейнере
make bots-up          # Telegram
make bots-up-viber    # Telegram + Viber (profile viber)
make bots-down
```

Проверка: `curl http://localhost:8091/health`

Если ранее вешали webhook на бота:

```bash
curl "https://api.telegram.org/bot<TOKEN>/deleteWebhook"
```

## Viber

Профиль `viber` в compose. Без `VIBER_AUTH_TOKEN` контейнер поднимается, но не отвечает в чат. Код и workspace-зависимости те же, что у Telegram.

## Файлы `requirements.txt` в `bots/*/`

Для Docker **не используются** (зависимости ставятся через `pip install` из `pyproject.toml` в Dockerfile). Файлы можно удалить или оставить как справку; источник истины — workspace и `uv.lock` в корне.
