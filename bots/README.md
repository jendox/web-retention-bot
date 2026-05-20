# Messenger bot sidecars

Отдельные лёгкие контейнеры для Telegram и Viber. **Не импортируют** код основного FastAPI-приложения — только `httpx`, `starlette`, `uvicorn` и общий клиент `shared/retention_api.py`.

## Архитектура

```text
Пользователь → «Подключить Telegram» в SPA
    → API создаёт одноразовый token в Redis
    → deep link https://t.me/retention_studio_bot?start=<token>

Пользователь → Start в боте
    → telegram-bot (polling/webhook)
    → POST /api/internal/messenger/telegram/complete-link
    → API сохраняет chat_id в notification_channels

Отправка уведомления (позже из dispatcher)
    → API POST http://telegram-bot:8091/v1/send { external_id: chat_id, text }
    → Bot API sendMessage
```

## Telegram (`retention_studio_bot`)

| Переменная | Описание |
|------------|----------|
| `TELEGRAM_BOT_TOKEN` | Токен от [@BotFather](https://t.me/BotFather) |
| `BOT_INTERNAL_SECRET` | Тот же, что `MESSENGER_BOTS__INTERNAL_SECRET` в API |
| `RETENTION_API_URL` | URL API, напр. `http://host.docker.internal:8000` |
| `TELEGRAM_MODE` | `polling` (dev) или `webhook` (prod) |

Порты: **8091** — health, `/v1/send`, `/telegram/webhook`.

## Viber (заготовка)

Профиль `viber` в compose. Без `VIBER_AUTH_TOKEN` контейнер поднимается, но не шлёт ответы.

Порты: **8092**.

## Запуск

```bash
# В .env корня репозитория:
# TELEGRAM_BOT_TOKEN=...
# MESSENGER_BOTS__INTERNAL_SECRET=...
# MESSENGER_BOTS__TELEGRAM_SERVICE_URL=http://localhost:8091

make bots-up          # только Telegram
make bots-up-viber    # Telegram + Viber (profile)

make backend-run      # API на :8000
```

Локально без Docker:

```bash
export TELEGRAM_BOT_TOKEN=...
export BOT_INTERNAL_SECRET=dev-bot-internal-secret-change-me
export RETENTION_API_URL=http://127.0.0.1:8000
cd bots/telegram && pip install -r requirements.txt
PYTHONPATH=/path/to/bots/telegram:/path/to/bots \
  uvicorn app.main:app --host 0.0.0.0 --port 8091
```

Скопируйте `shared/retention_api.py` в `bots/telegram/` или задайте `PYTHONPATH` на каталог `bots`, где лежит `retention_api.py` (в Docker он копируется в `/app/retention_api.py`).
