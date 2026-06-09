import functools
from typing import Any, Callable

from sqlalchemy.ext.asyncio import AsyncSession


class BaseService:
    def __init__(self, db: AsyncSession) -> None:
        self.db: AsyncSession = db

    @staticmethod
    def transaction(func: Callable[[Any], Any]) -> Any:
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            try:
                result = await func(self, *args, **kwargs)
                await self.db.commit()
                return result
            except Exception as e:
                await self.db.rollback()
                raise e

        return wrapper
