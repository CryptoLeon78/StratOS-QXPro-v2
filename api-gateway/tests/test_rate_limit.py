import fakeredis
import pytest

from gateway.rate_limit import RateLimitExceeded, check_rate_limit


@pytest.mark.asyncio
async def test_allows_requests_under_the_limit() -> None:
    redis = fakeredis.FakeAsyncRedis()
    for _ in range(5):
        await check_rate_limit(redis, "1.2.3.4", limit_per_minute=5)


@pytest.mark.asyncio
async def test_blocks_the_request_that_exceeds_the_limit() -> None:
    redis = fakeredis.FakeAsyncRedis()
    for _ in range(5):
        await check_rate_limit(redis, "1.2.3.4", limit_per_minute=5)
    with pytest.raises(RateLimitExceeded):
        await check_rate_limit(redis, "1.2.3.4", limit_per_minute=5)


@pytest.mark.asyncio
async def test_counters_are_independent_per_key() -> None:
    redis = fakeredis.FakeAsyncRedis()
    for _ in range(5):
        await check_rate_limit(redis, "1.2.3.4", limit_per_minute=5)
    # otra IP no deberia verse afectada por el consumo de la primera.
    await check_rate_limit(redis, "5.6.7.8", limit_per_minute=5)


@pytest.mark.asyncio
async def test_window_expires_after_60_seconds() -> None:
    redis = fakeredis.FakeAsyncRedis()
    await check_rate_limit(redis, "1.2.3.4", limit_per_minute=1)
    ttl = await redis.ttl("ratelimit:1.2.3.4")
    assert 0 < ttl <= 60
