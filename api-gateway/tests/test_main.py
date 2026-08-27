from collections.abc import AsyncIterator

import fakeredis
import httpx
import pytest
from redis.asyncio import Redis

from gateway.config import Settings, get_settings
from gateway.http_client import get_http_client
from gateway.main import app
from gateway.redis_client import get_redis


def _upstream_echo(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"path": request.url.path, "method": request.method})


@pytest.fixture
def redis() -> Redis:
    return fakeredis.FakeAsyncRedis()  # type: ignore[no-any-return]


@pytest.fixture(autouse=True)
def _clear_overrides_after_each_test() -> AsyncIterator[None]:
    yield
    app.dependency_overrides.clear()


def _override_settings(rate_limit_per_minute: int) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        redis_url="redis://unused",
        core_engine_url="http://core-engine",
        rate_limit_per_minute=rate_limit_per_minute,
    )


def _override_redis(redis: Redis) -> None:
    app.dependency_overrides[get_redis] = lambda: redis


def _override_upstream(handler: object = None) -> None:
    async def _get_http_client_override() -> AsyncIterator[httpx.AsyncClient]:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler or _upstream_echo)  # type: ignore[arg-type]
        ) as client:
            yield client

    app.dependency_overrides[get_http_client] = _get_http_client_override


@pytest.mark.asyncio
async def test_health_is_answered_locally_not_proxied() -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://gateway"
    ) as client:
        response = await client.get("/health")
    assert response.json() == {"status": "ok", "service": "api-gateway"}


@pytest.mark.asyncio
async def test_forwards_an_arbitrary_path_to_core_engine(redis: Redis) -> None:
    _override_settings(rate_limit_per_minute=100)
    _override_redis(redis)
    _override_upstream()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://gateway"
    ) as client:
        response = await client.get("/api/v1/header/summary")

    assert response.status_code == 200
    assert response.json() == {"path": "/api/v1/header/summary", "method": "GET"}


@pytest.mark.asyncio
async def test_returns_429_once_the_rate_limit_is_exceeded(redis: Redis) -> None:
    _override_settings(rate_limit_per_minute=1)
    _override_redis(redis)
    _override_upstream()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://gateway"
    ) as client:
        first = await client.get("/anything")
        second = await client.get("/anything")

    assert first.status_code == 200
    assert second.status_code == 429
