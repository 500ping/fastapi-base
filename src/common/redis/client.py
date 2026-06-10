from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from fastapi import status
from redis.asyncio import Redis
from redis.exceptions import LockError

from src.common.configs.logging import get_logger
from src.common.configs.settings import get_settings
from src.common.enums.message_enum import ExceptionMessageEnum
from src.common.exceptions.api_exception import APIException

settings = get_settings()
logger = get_logger(__name__)

_redis_client: Optional[Redis] = None


def get_redis() -> Redis:
    """Return the shared async Redis client (lazily created)."""
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


@asynccontextmanager
async def distributed_lock(
    name: str,
    *,
    timeout: Optional[float] = None,
    blocking_timeout: Optional[float] = None,
) -> AsyncIterator[None]:
    """Acquire a Redis-backed distributed lock for the duration of the block.

    ``timeout`` caps how long the lock is held before Redis auto-releases it
    (guards against a crashed holder). ``blocking_timeout`` caps how long we
    wait to acquire it; if it can't be acquired in time we raise a 503 so the
    caller can retry rather than block forever.
    """
    lock = get_redis().lock(
        f"lock:{name}",
        timeout=timeout if timeout is not None else settings.redis_lock_timeout,
        blocking_timeout=(
            blocking_timeout
            if blocking_timeout is not None
            else settings.redis_lock_blocking_timeout
        ),
    )
    acquired = await lock.acquire()
    if not acquired:
        logger.warning("Could not acquire distributed lock", lock=name)
        raise APIException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            ExceptionMessageEnum.LOCK_UNAVAILABLE,
        )
    try:
        yield
    finally:
        try:
            await lock.release()
        except LockError:
            # Lock already expired (held past ``timeout``); nothing to release.
            logger.warning("Distributed lock expired before release", lock=name)
