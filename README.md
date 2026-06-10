# fastapi-base

An opinionated, async-first FastAPI starter. It ships a clean feature-module
layout, JWT auth, a transactional service layer, structured JSON logging, and a
test setup backed by real PostgreSQL via testcontainers — so you can start
building features instead of wiring boilerplate.

## Features

- **Async everything** — FastAPI + SQLAlchemy 2 async + psycopg3.
- **Auth module** (reference feature) — signup, signin, refresh, and logout with
  JWT access/refresh tokens and DB-backed token blacklisting.
- **Course module** — teachers, students, and classes built on the `User` model,
  with student self-enrollment guarded by a **Redis distributed lock** so a class
  never exceeds its capacity, even under concurrent requests.
- **Transactional services** — `BaseService.transaction` wraps a unit of work in
  one commit/rollback.
- **Consistent API envelope** — `SuccessResponse[T]` and a single `APIException`
  flow with centralized error messages.
- **Structured logging** — structlog JSON output with a per-request id.
- **Startup DB health check** — retries with tenacity, aborts if the DB is down.
- **Migrations** — Alembic (async) with autogenerate.
- **Tests** — pytest + testcontainers (a throwaway Postgres and Redis per run).

## Requirements

- Python **3.14+**
- [uv](https://docs.astral.sh/uv/)
- Docker (for the local PostgreSQL + Redis stack and the test suite)

## Setup

```bash
# 1. Install dependencies
make install            # uv sync

# 2. Create your env file and adjust as needed
cp .env.example .env

# 3. Start the local stack (PostgreSQL + Redis)
make up

# 4. Apply database migrations
make migrate

# 5. Run the app (http://127.0.0.1:8000)
make run
```

Interactive API docs: <http://127.0.0.1:8000/docs>.
Health check: `GET /api/v1/health`.

## Configuration

Settings come from environment variables / `.env` (see `.env.example`). Key ones:

| Variable                   | Default                                   | Description                          |
| -------------------------- | ----------------------------------------- | ------------------------------------ |
| `DEBUG`                    | `1`                                       | Debug mode (verbose logs, SQL echo). |
| `DATABASE_URL`             | `postgresql+psycopg://...localhost:5432/fastapi_base` | Async Postgres DSN.      |
| `REDIS_URL`                | `redis://localhost:6379/0`                | Redis DSN (distributed locks).       |
| `JWT_SECRET_KEY`           | placeholder                               | **Set a strong 32+ byte secret.**    |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30`                                   | Access token lifetime.               |
| `REFRESH_TOKEN_EXPIRE_DAYS`   | `7`                                    | Refresh token lifetime.              |
| `DB_CONNECT_MAX_RETRIES`   | `5`                                       | Startup DB connection attempts.      |

## Common commands

Run `make help` for the full list.

| Command                    | What it does                                 |
| -------------------------- | -------------------------------------------- |
| `make run`                 | Run the app with autoreload.                 |
| `make up` / `make down`    | Start / stop the local compose stack.        |
| `make migrate`             | Apply all migrations.                        |
| `make migration m="..."`   | Autogenerate a migration.                    |
| `make test`                | Run the test suite (needs Docker).           |
| `make coverage`            | Run tests with a coverage report.            |
| `make lint` / `make format`| Lint / format with ruff.                     |

## Auth flow

All routes are under `/api/v1/auth`:

1. `POST /signup` — create an account.
2. `POST /signin` — get an access + refresh token pair.
3. `POST /refresh` — exchange a refresh token for a new pair.
4. `POST /logout` — revoke the current access and refresh tokens (blacklisted).

## Course module

A small domain feature built on top of `User` — there is no separate role table:
a **teacher** is simply whoever owns (created) a class, and a **student** is any
user who enrolls. All routes require a valid access token and act on the
authenticated user. They live under `/api/v1/courses`:

1. `POST /classes` — the current user creates a class they own (teacher).
2. `GET /classes` — list classes (paginated). Optional `relation` query param
   scopes the result to the current user: `owner` (classes they teach), `joiner`
   (classes they joined), or omitted for all classes. Supports `page` / `size`.
3. `GET /classes/{id}` — class detail, including `capacity` and `enrolled_count`.
4. `GET /classes/{id}/students` — list the students enrolled in a class.
5. `POST /classes/{id}/enroll` — the current user enrolls **themselves** as a student.

A class holds up to **40 students** (`MAX_STUDENTS_PER_CLASS`). The capacity check
is a read-modify-write, so concurrent enrollments could otherwise race past the
limit. Enrollment therefore runs under a **Redis distributed lock** (see
`src/common/redis/client.py`) that spans the count, the insert, and the commit —
so the cap holds even across multiple app instances.

## Testing

```bash
make test
```

Tests spin up disposable PostgreSQL and Redis containers (Docker required); each
test runs against a fresh schema. No local database is touched.

### Coverage

```bash
make coverage        # terminal report (shows missing lines)
make coverage-html   # writes htmlcov/index.html for a line-by-line view
```

Coverage is scoped to `src/` with branch coverage enabled (configured under
`[tool.coverage.*]` in `pyproject.toml`).

## Project structure & conventions

Source lives in `src/` with one package per feature and shared infrastructure in
`src/common/`. Before adding a feature, read **[AGENTS.md](AGENTS.md)** — it
documents the module structure and the rules for models, services, DTOs, routers,
errors, settings, and async code.
