from typing import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from tenacity import (
    RetryCallState,
    retry,
    stop_after_attempt,
    wait_fixed,
)

from src.common.configs.logging import get_logger
from src.common.configs.settings import get_settings

settings = get_settings()
logger = get_logger(__name__)

# Force every connection's session timezone to UTC so timestamps are stored and
# read back in UTC (naive datetimes written to timestamptz columns and func.now()
# are interpreted as UTC, never the server's local timezone).
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
    connect_args={"options": "-c timezone=utc"},
)
AsyncSessionLocal = async_sessionmaker(
    engine, autocommit=False, autoflush=False, expire_on_commit=False
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yield a database session for the duration of a request."""
    async with AsyncSessionLocal() as session:
        yield session


def _log_failed_attempt(retry_state: RetryCallState) -> None:
    outcome = retry_state.outcome
    if outcome is not None and outcome.failed:
        logger.warning(
            "Database connection failed",
            attempt=retry_state.attempt_number,
            max_retries=settings.db_connect_max_retries,
            error=str(outcome.exception()),
        )


async def check_database_connection() -> None:
    """Verify the database is reachable, retrying with a fixed delay.

    Raises the last error after exhausting ``db_connect_max_retries`` so the
    caller (the app lifespan) can abort startup rather than serve traffic
    against an unreachable database.
    """

    @retry(
        stop=stop_after_attempt(settings.db_connect_max_retries),
        wait=wait_fixed(settings.db_connect_retry_delay),
        after=_log_failed_attempt,
        reraise=True,
    )
    async def _connect() -> None:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

    try:
        await _connect()
        logger.info("Database connection established")
    except Exception:
        logger.error("Database unreachable after retries; aborting startup")
        raise
