import os
from typing import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

# Import models so their tables register on BaseModel.metadata.
import src.auth.models  # noqa: F401
import src.course.models  # noqa: F401
from src.common.database.session import get_db
from src.common.models import BaseModel


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    """Start a throwaway PostgreSQL container for the whole test session."""
    with PostgresContainer("postgres:17", driver="psycopg") as postgres:
        url = postgres.get_connection_url()
        # Mirror into the environment so anything reading settings sees the
        # test database too.
        os.environ["DATABASE_URL"] = url
        yield url


@pytest.fixture(scope="session")
def redis_url() -> Iterator[str]:
    """Start a throwaway Redis container for the whole test session."""
    with RedisContainer("redis:7") as redis:
        host = redis.get_container_host_ip()
        port = redis.get_exposed_port(6379)
        url = f"redis://{host}:{port}/0"
        os.environ["REDIS_URL"] = url
        yield url


@pytest_asyncio.fixture
async def redis_client(redis_url: str) -> AsyncIterator[Redis]:
    """Point the app's Redis client at the test container, fresh per test.

    Created inside the test's event loop so the async client binds to the right
    loop, and the DB is flushed so leftover lock keys never bleed across tests.
    """
    import src.common.redis.client as redis_module

    client = Redis.from_url(redis_url, decode_responses=True)
    await client.flushdb()
    redis_module._redis_client = client
    try:
        yield client
    finally:
        await client.aclose()
        redis_module._redis_client = None


@pytest_asyncio.fixture
async def db_engine(postgres_url: str) -> AsyncIterator[AsyncEngine]:
    """Engine bound to the test container, with a fresh schema per test."""
    engine = create_async_engine(
        postgres_url, connect_args={"options": "-c timezone=utc"}
    )
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)
    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(BaseModel.metadata.drop_all)
        await engine.dispose()


@pytest.fixture
def session_factory(db_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(db_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """A plain session for exercising services/models directly."""
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncClient]:
    """HTTP client with ``get_db`` overridden to use the test database."""
    from src import app

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
