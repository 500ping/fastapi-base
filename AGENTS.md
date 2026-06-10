# AGENTS.md

Conventions for working in this FastAPI base. Follow them when adding features so
the codebase stays consistent. Examples below reference the `auth` module, which
is the reference implementation.

## Stack & tooling

- **Python 3.14**, **FastAPI**, **SQLAlchemy 2 (async)** + **psycopg3**
  (`postgresql+psycopg://`), **Pydantic v2** / **pydantic-settings**, **Alembic**,
  **structlog** (JSON logs), **PyJWT**, **pwdlib[bcrypt]**, **tenacity**.
- **uv** manages dependencies: `uv add <pkg>` (runtime), `uv add --dev <pkg>` (dev).
  Never hand-edit installed packages.
- **ruff** lints/formats. **pytest** + **testcontainers** for tests.
- Use the **Makefile** for everything: `make help` lists targets
  (`up`, `down`, `migrate`, `migration m="..."`, `test`, `lint`, `format`, `run`).

## Project layout

```
src/
  __init__.py            # app factory: create_app(), lifespan, router mounting
  common/                # cross-cutting building blocks (see below)
  <feature>/             # one package per feature/domain (e.g. auth)
migrations/              # Alembic (async env.py)
tests/<feature>/         # tests mirror the source tree
```

### `src/common/` (shared infrastructure — extend, don't fork)

- `configs/settings.py` — `Settings` (pydantic-settings) + cached `get_settings()`.
- `configs/logging.py` — structlog setup, `get_logger(__name__)`, request-id context.
- `database/session.py` — async `engine`, `AsyncSessionLocal`, `get_db` dependency,
  `check_database_connection()` (startup retry).
- `models.py` — `BaseModel`: the **single** declarative base (id/created_at/updated_at).
- `services.py` — `BaseService` + `@BaseService.transaction`.
- `dtos/requests/pagination.py` — `PaginationParams` (reusable `page`/`size` query base).
- `dtos/responses/success.py` — `SuccessResponse[T]` (generic) and `Pagination`.
- `enums/message_enum.py` — `ExceptionMessageEnum`: all user-facing error strings.
- `exceptions/api_exception.py` — `APIException(http_status, message)`.
- `handlers/exception_handler.py` — exception → JSON handlers.
- `middlewares/log_middleware.py` — one structured log line per request.

## Creating a new module

A feature module is a package under `src/`. Use this structure (omit files you
don't need):

```
src/<feature>/
  __init__.py
  routers.py             # APIRouter + endpoints
  services.py            # business logic (extends BaseService)
  models.py              # SQLAlchemy models (extend BaseModel)
  deps.py                # FastAPI dependencies (auth guards, etc.)
  enums.py               # StrEnum types
  constants.py           # scalar constants (claim keys, header names, ...)
  utils.py               # pure, stateless helpers
  openapi.py             # OpenAPI response examples (optional)
  dtos/
    __init__.py
    requests/__init__.py
    requests/<feature>.py
    responses/__init__.py
    responses/<feature>.py
```

**File naming:** plural for collections of definitions — `models.py`, `services.py`,
`routers.py`, `deps.py`, `utils.py`. Singular for `enums.py`, `constants.py`.
Enums go in `enums.py`; scalar constants in `constants.py`.

**Mount the router** in `src/__init__.py` → `register_routers`, on the shared
`/api/v1` base router:

```python
from src.<feature>.routers import router as <feature>_router
base_router.include_router(<feature>_router, prefix="/<feature>", tags=["<Feature>"])
```

The router itself declares **no prefix** — the prefix/tags are set at mount time.

## Creating a model

- Extend `BaseModel` from `src.common.models` — **never** declare another
  `DeclarativeBase`. A single metadata is what makes Alembic autogenerate work.
- `BaseModel` provides `id` (BigInteger PK), `created_at`, `updated_at`, and a
  default `__tablename__` (class name lowercased). Set an explicit plural
  `__tablename__` when you want pluralization (e.g. `User` → `"users"`).
- Use typed `Mapped[...]` / `mapped_column(...)`.

```python
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from src.common.models import BaseModel

class Widget(BaseModel):
    __tablename__ = "widgets"
    name: Mapped[str] = mapped_column(String(255), index=True)
```

**After adding a model module**, make it importable from `migrations/env.py` (it
imports feature model modules so tables register on `BaseModel.metadata`), then:

```
make migration m="add widgets"   # autogenerate
make migrate                     # apply
```

Review the generated migration before committing — autogenerate is a starting point.

## Creating a service

- Extend `BaseService` (gives you `self.db` and the `transaction` decorator).
- Decorate the **public ("main") method** with `@BaseService.transaction`. It owns
  the single `commit()` and rolls back on any exception. Do **not** call
  `self.db.commit()` yourself.
- When you must persist a record mid-method (e.g. to read its generated `id`),
  use `await self.db.flush()` — never `commit()`.
- Helper methods (prefixed `_`) stay **undecorated** so they enlist in the
  caller's transaction.
- Read-only methods need no decorator.
- Raise `APIException(<status>, ExceptionMessageEnum.X)` for expected errors.

```python
from src.common.services import BaseService

class WidgetService(BaseService):
    @BaseService.transaction
    async def create(self, req: CreateWidgetRequest) -> Widget:
        widget = Widget(name=req.name)
        self.db.add(widget)
        await self.db.flush()        # populate id within the transaction
        return widget
```

## DTOs (requests & responses)

- Pydantic models. Requests in `dtos/requests/`, responses in `dtos/responses/`.
- Add request examples with `Field(examples=[...])`.
- Routes return the shared envelope `SuccessResponse[T]`; set
  `response_model=SuccessResponse[T]` and `response_model_exclude_none=True`.
  `SuccessResponse` is generic — always parametrize it (`SuccessResponse[WidgetResponse]`),
  otherwise the nested `data` is dropped.

### Pagination

- For list endpoints, **reuse** `PaginationParams` from
  `src/common/dtos/requests/pagination.py` — don't redeclare `page`/`size`. It
  provides validated `page` (≥1) and `size` (1–`MAX_PAGE_SIZE`) fields plus
  `offset`/`limit` helpers.
- Add endpoint-specific (optional) filters by **subclassing** it, then accept the
  subclass as query params with `Annotated[..., Query()]` (FastAPI flattens the
  model into individual query params):

  ```python
  class ListWidgetsParams(PaginationParams):
      status: Optional[WidgetStatus] = None

  @router.get("", response_model=SuccessResponse[list[WidgetResponse]], ...)
  async def list_widgets(
      db: DbSession, params: Annotated[ListWidgetsParams, Query()]
  ) -> SuccessResponse:
      rows, total = await WidgetService(db).list_widgets(params.status, params.page, params.size)
      return SuccessResponse(
          data=[...],
          pagination=Pagination(page=params.page, size=params.size, total=total),
      )
  ```

- The service stays decoupled from the DTO: take plain `page`/`size` ints and
  return `(rows, total)` so the route can build the `Pagination` envelope.

## Routers

- `router = APIRouter()` (no prefix). Define `DbSession = Annotated[AsyncSession, Depends(get_db)]`.
- Document responses **including errors** via `responses=...`; keep the example
  payloads in `openapi.py` and source error messages from `ExceptionMessageEnum`.

```python
@router.post("", response_model=SuccessResponse[WidgetResponse],
             response_model_exclude_none=True, responses=CREATE_RESPONSES)
async def create_widget(req: CreateWidgetRequest, db: DbSession) -> SuccessResponse:
    widget = await WidgetService(db).create(req)
    return SuccessResponse(msg="Widget created", data=WidgetResponse.model_validate(widget))
```

## Errors & messages

- Every user-facing error string lives in `ExceptionMessageEnum` (a `StrEnum`).
  Reuse existing entries; add new ones there — keep handlers and OpenAPI docs in sync.
- Raise `APIException`; never return raw error dicts from routes.
- Exception handlers are registered in `src/__init__.py`. `APIException` is
  registered **before** the `Exception` catch-all so expected errors return clean
  JSON (no 500 traceback) while unexpected ones become 500s.

## Settings

- Add config fields to `Settings` with sensible defaults, then mirror the keys in
  both `.env` and `.env.example`. Read config via `get_settings()` (cached).
- Don't read `os.environ` directly in app code — go through `Settings`.

## Async conventions

This is a fully async app. The event loop must never block.

- Routes, services, dependencies, and DB access are `async` and use `await`.
- Get DB sessions **only** via the `get_db` dependency — never instantiate
  sessions ad hoc inside a route or service.
- Use the SQLAlchemy **async** API (`await self.db.execute(select(...))`,
  `await self.db.get(...)`, `await self.db.flush()`).
- **If something cannot be awaited** (a blocking or CPU-bound synchronous call —
  e.g. password hashing, image processing, a sync-only third-party client),
  offload it so it doesn't block the loop:

  ```python
  import asyncio
  hashed = await asyncio.to_thread(hash_password, raw_password)
  ```

  Prefer a native async library when one exists; fall back to `asyncio.to_thread`
  for unavoidable blocking calls. Never call `time.sleep`, blocking HTTP/DB
  drivers, or other blocking I/O directly in async code (use `asyncio.sleep`,
  async clients, etc.).

## Logging

- `logger = get_logger(__name__)`. Log with structured key-values, not f-strings:
  `logger.info("widget created", widget_id=widget.id)`. Output is JSON and the
  request id is attached automatically.
- Keep keys low-cardinality where they matter as Loki labels (`level`, `logger`).
  Per-entity values (ids, request_id) belong in the line, not as labels.
- Logs go to **stdout** as JSON. The opt-in `make dev` stack (app + Loki +
  Promtail + Grafana, configured under `docker/`) scrapes container stdout into
  Loki; query in Grafana Explore with LogQL. See the README for details. Don't
  add file logging or alternate sinks — keep stdout JSON as the single source.

## Testing

- Tests live in `tests/<feature>/` mirroring `src/`. Shared fixtures are in
  `tests/conftest.py`: `client` (httpx against the app with `get_db` overridden),
  `db_session`, `db_engine`, `session_factory`.
- PostgreSQL is provided by **testcontainers** (Docker required); each test gets a
  fresh schema. `asyncio_mode = "auto"` — write `async def test_...` directly.
- Cover both the HTTP flow (via `client`) and units (services/utils via `db_session`).
- Run with `make test` (needs Docker). Keep `make lint` clean.

## Definition of done for a new feature

1. Module created with the structure above; router mounted under `/api/v1`.
2. Models extend `BaseModel`; migration generated, applied, and committed.
3. Services use `@BaseService.transaction`; expected errors via `APIException` +
   `ExceptionMessageEnum`.
4. New settings mirrored in `.env` / `.env.example`.
5. Tests added under `tests/<feature>/`; `make test` and `make lint` pass.
