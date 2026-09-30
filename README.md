# Retention Studio

**Full-stack CRM, booking, notification, and retention analytics platform for independent service professionals.**

Retention Studio is a SaaS-style application for professionals who manage recurring clients and appointments. It combines scheduling, customer management, self-service booking, notifications, attendance tracking, and retention analytics in one system.

The project consists of a FastAPI backend, React frontend, PostgreSQL, Redis, and Celery workers for background processing.

## Product overview

Retention Studio supports two main user experiences:

- **Professional workspace** — manage services, working hours, clients, appointments, notifications, and business analytics.
- **Client workspace** — view professionals, book available slots, manage appointments, and review visit history.

## Key features

### Authentication and security

- Professional and client registration
- Email verification
- Server-side session authentication
- CSRF protection for state-changing requests
- Password reset and password change
- Rate limiting on sensitive authentication endpoints

### Professional workspace

- Profile and business settings
- Weekly working schedule
- Service catalog with price, duration, currency, and active status
- Client database
- Client invitations
- Client detail pages with booking history
- Create, reschedule, confirm, and cancel appointments
- Attendance and no-show tracking
- Action comments
- Notification center and preferences
- Revenue and retention analytics

### Client workspace

- Connected professionals
- Professional contact cards
- Visit history
- Self-service booking from available time slots
- Appointment rescheduling and cancellation
- Client profile
- Notification center and preferences

### Notifications

The notification pipeline supports:

- in-app notifications
- email
- messenger notifications when a channel is connected

Background workers are used for delivery and scheduled workflows.

### Analytics

The analytics module includes:

- revenue from completed appointments
- average ticket
- completed, cancelled, and missed appointments
- new vs returning clients
- lost revenue from cancellations and no-shows
- daily revenue trend
- service performance
- clients due for reactivation
- schedule utilization

Money values use booking snapshots and remain grouped by currency.

## Architecture

```text
src/app/
├── domain models
├── use cases
├── repositories
├── API routes
├── Celery tasks
└── admin integration

frontend/
├── React
├── Vite
├── TanStack Query
└── React Router

bots/
└── optional messenger sidecars

tests/
└── backend unit/API tests

deploy/
└── local infrastructure and service dependencies
```

The application separates API/domain logic from background delivery and frontend concerns. Messaging integrations are handled through optional sidecars rather than being tightly coupled to the core web process.

## Booking flow

```text
Professional defines schedule + services
  ↓
Client requests availability
  ↓
Backend calculates valid slots
  ↓
Client creates booking
  ↓
Booking is persisted
  ↓
Notification pipeline runs
  ↓
Professional and client manage the appointment lifecycle
  ↓
Completed / cancelled / no-show outcome feeds analytics
```

## Background jobs

Celery worker/beat are used for:

- email and messenger delivery
- in-app notification workflows
- automatic completion of past appointments
- scheduled notification processing
- password-reset email delivery through the shared notification pipeline

## API

Public application routes are grouped under `/api`.

Main areas include:

```text
/api/auth/*
/api/invitations/*
/api/master/profile
/api/master/schedule
/api/master/clients
/api/master/services
/api/master/bookings
/api/master/notifications
/api/master/notification-settings
/api/master/analytics
/api/client/profile
/api/client/masters
/api/client/bookings
/api/client/availability
/api/client/notifications
/api/client/notification-settings
/api/internal/messenger/*
```

Domain errors are returned through a structured contract:

```json
{
  "code": "domain.error_code",
  "detail": "English fallback",
  "context": {}
}
```

## Tech stack

| Area | Technologies |
|---|---|
| Backend | Python, FastAPI |
| Frontend | React, Vite, TanStack Query, React Router |
| Database | PostgreSQL |
| Background jobs | Celery, Redis |
| Migrations | Alembic |
| Admin | SQLAdmin |
| Email testing | smtp4dev |
| Deployment / local infra | Docker Compose |

## Local development

### Backend

```bash
make backend-install
cp .env.example .env
make infra-up
make backend-migrate
make backend-run
```

### Frontend

```bash
make frontend-install
make frontend-run
```

Default development endpoints:

```text
API:       http://localhost:8000
Frontend:  http://localhost:5173
smtp4dev:  http://localhost:5000
```

### Background workers

```bash
make celery-worker
make celery-beat
```

## Testing and checks

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

Run all checks:

```bash
make lint
make test
```

The backend test workflow uses a dedicated PostgreSQL test database and a separate Redis database rather than reusing development data.

## Project status

Retention Studio is an actively developed SaaS MVP. The core professional/client flows, booking lifecycle, notification pipeline, and analytics are implemented.

Current deployment-readiness work includes:

- production/staging environment preparation
- SMTP deliverability setup
- operational logging/monitoring
- backup and restore validation
- end-to-end smoke testing

Potential product extensions include public booking, reactivation reminders, additional messaging channels, deeper analytics, and broader E2E coverage.

## Documentation

- [`docs/analytics_plan.md`](docs/analytics_plan.md) — analytics implementation and next iterations
- [`docs/refactor_plan.md`](docs/refactor_plan.md) — domain/application cleanup notes
- [`docs/mvp_readiness.md`](docs/mvp_readiness.md) — deployment-readiness checklist
- [`docs/test_data.md`](docs/test_data.md) — analytics test-data workflow

## Project focus

Retention Studio demonstrates full-stack backend-oriented product development: authentication, scheduling, domain workflows, asynchronous notifications, analytics, and a separate modern frontend around a FastAPI API.