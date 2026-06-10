import pytest
from redis.asyncio import Redis

from src.common.redis import client as redis_module


async def test_check_connection_succeeds(redis_client: Redis) -> None:
    # ``redis_client`` points the module at the reachable test container.
    # Should not raise when Redis is reachable.
    await redis_module.check_redis_connection()


async def test_check_connection_retries_then_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bad_client = Redis.from_url("redis://localhost:6399/0", decode_responses=True)
    monkeypatch.setattr(redis_module, "_redis_client", bad_client)
    monkeypatch.setattr(redis_module.settings, "redis_connect_max_retries", 2)
    monkeypatch.setattr(redis_module.settings, "redis_connect_retry_delay", 0.01)

    with pytest.raises(Exception):
        await redis_module.check_redis_connection()

    await bad_client.aclose()
