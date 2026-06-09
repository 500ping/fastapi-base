import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.common.services import BaseService


class _DemoService(BaseService):
    @BaseService.transaction
    async def add_user(self, email: str) -> User:
        user = User(email=email, hashed_password="x")
        self.db.add(user)
        await self.db.flush()
        return user

    @BaseService.transaction
    async def add_then_fail(self, email: str) -> None:
        self.db.add(User(email=email, hashed_password="x"))
        await self.db.flush()
        raise RuntimeError("boom")


async def _user_count(db: AsyncSession) -> int:
    result = await db.execute(select(func.count()).select_from(User))
    return result.scalar_one()


async def test_transaction_commits_on_success(db_session: AsyncSession) -> None:
    user = await _DemoService(db_session).add_user("ok@example.com")

    assert user.id is not None  # flush populated the generated id
    assert await _user_count(db_session) == 1


async def test_transaction_rolls_back_on_error(db_session: AsyncSession) -> None:
    with pytest.raises(RuntimeError, match="boom"):
        await _DemoService(db_session).add_then_fail("rollback@example.com")

    assert await _user_count(db_session) == 0
