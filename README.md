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
- **Log aggregation** (opt-in) — a Grafana + Loki + Promtail stack that scrapes
  the containerized app's JSON logs (`make dev`).
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
| `REDIS_CONNECT_MAX_RETRIES`| `5`                                       | Startup Redis connection attempts.   |

## Common commands

Run `make help` for the full list.

| Command                    | What it does                                 |
| -------------------------- | -------------------------------------------- |
| `make run`                 | Run the app with autoreload.                 |
| `make up` / `make down`    | Start / stop the local compose stack.        |
| `make dev`                 | Start the full stack with log aggregation.   |
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

## Log aggregation (Grafana Loki)

The app logs structured JSON to stdout. For centralized, queryable logs there's an
opt-in observability stack:

```bash
make dev            # builds + runs: app + Postgres + Redis + Loki + Promtail + Grafana
```

- **App** runs as a container (so its stdout can be scraped) at
  <http://localhost:8000/docs>. Migrations run automatically on startup.
- **Promtail** discovers containers via the Docker socket and pushes their stdout
  to **Loki**. Only the `app`, `db` and `redis` containers are scraped. The
  **app** emits JSON, so its low-cardinality fields (`level`, `logger`,
  `compose_service`, `container`) become labels while `request_id`/`message` stay
  in the line; `db`/`redis` are plain text and pass through untouched.
- **Grafana** is at <http://localhost:3000> (anonymous admin, no login).
  Everything is **pre-provisioned**, so there's nothing to set up each run:
  - Loki is the default datasource.
  - An **App Logs** dashboard (the home page) with a service/level filter, a
    log-volume-by-level graph, error/total counters, and a live log panel.

  To explore ad-hoc, open **Explore** and query with LogQL, e.g.:

  ```logql
  {compose_service="app"} | json | level="error"
  {container="fastapi_base_app"} |= "request_id"
  ```

Stop it with `make dev-down`. The whole stack is self-contained in
`docker-compose.dev.yml` (db + redis + app + Loki + Promtail + Grafana), so a dev
deploy is a single `docker compose -f docker-compose.dev.yml up -d --build`.
`docker-compose.local.yml` stays lightweight (db + redis only) for host dev with
`make up` + `make run`. Config lives under `docker/` (Loki, Promtail, and Grafana
datasource + dashboard provisioning) and the app image is built from the root
`Dockerfile`. The Grafana dashboard JSON is the source of truth
(`docker/grafana/dashboards/app-logs.json`); edit that file to change it — UI
edits aren't persisted.

> For plain host development (hot reload, no aggregation) keep using `make up` +
> `make run`; those host logs are **not** captured by Promtail, which scrapes
> Docker containers only.

## Project structure & conventions

Source lives in `src/` with one package per feature and shared infrastructure in
`src/common/`. Before adding a feature, read **[AGENTS.md](AGENTS.md)** — it
documents the module structure and the rules for models, services, DTOs, routers,
errors, settings, and async code.
