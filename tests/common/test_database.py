from datetime import timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from src.auth.models import User
from src.common.database import session as session_module


async def test_check_connection_succeeds(
    db_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(session_module, "engine", db_engine)

    # Should not raise when the database is reachable.
    await session_module.check_database_connection()


async def test_check_connection_retries_then_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bad_engine = create_async_engine(
        "postgresql+psycopg://postgres:postgres@localhost:5999/missing"
    )
    monkeypatch.setattr(session_module, "engine", bad_engine)
    monkeypatch.setattr(session_module.settings, "db_connect_max_retries", 2)
    monkeypatch.setattr(session_module.settings, "db_connect_retry_delay", 0.01)

    with pytest.raises(Exception):
        await session_module.check_database_connection()

    await bad_engine.dispose()


async def test_session_timezone_is_utc(db_session: AsyncSession) -> None:
    tz = (await db_session.execute(text("SHOW timezone"))).scalar_one()

    assert tz == "UTC"


async def test_timestamps_saved_in_utc(db_session: AsyncSession) -> None:
    user = User(email="tz@example.com", hashed_password="x")
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)

    # Server-generated timestamps come back timezone-aware in UTC.
    assert user.created_at.tzinfo is not None
    assert user.created_at.utcoffset() == timezone.utc.utcoffset(None)
