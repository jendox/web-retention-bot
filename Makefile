DOCKER_COMPOSE = docker compose -f deploy/docker-compose.dev.yml
DOCKER_COMPOSE_BOTS = docker compose -f deploy/docker-compose.bots.yml

infra-up:
	$(DOCKER_COMPOSE) up -d

infra-down:
	$(DOCKER_COMPOSE) down

infra-clean:
	$(DOCKER_COMPOSE) down -v

bots-up:
	$(DOCKER_COMPOSE_BOTS) up -d --build telegram-bot

bots-up-viber:
	$(DOCKER_COMPOSE_BOTS) --profile viber up -d --build

bots-down:
	$(DOCKER_COMPOSE_BOTS) down

backend-install:
	uv sync

backend-migrate:
	uv run alembic -c alembic.ini upgrade head

backend-run:
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --app-dir src

# Celery: beat only enqueues periodic tasks; worker executes them (both terminals required).
celery-worker:
	PYTHONPATH=src uv run celery -A app.worker.celery_app worker -l info

celery-beat:
	PYTHONPATH=src uv run celery -A app.worker.celery_app beat -l info

backend-test:
	uv run pytest

backend-lint:
	uv run ruff check src tests

backend-fix:
	uv run ruff check --fix src

frontend-install:
	cd frontend && npm install

frontend-run:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

frontend-lint:
	cd frontend && npm run lint

frontend-test:
	cd frontend && npm run test

frontend-test-check:
	cd frontend && npm run lint

test: backend-test frontend-test-check frontend-test

lint: backend-lint frontend-lint
