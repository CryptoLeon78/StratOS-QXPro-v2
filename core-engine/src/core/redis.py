"""Cliente Redis compartido para dependencias FastAPI (routers/*, WS) --
mismo patron singleton que `db/base.py::engine` (una conexion reutilizada,
no una nueva por request)."""

from collections.abc import AsyncIterator

from redis.asyncio import Redis

from core.config import get_settings

_client: Redis | None = None


def get_redis_client() -> Redis:
    global _client
    if _client is None:
        _client = Redis.from_url(get_settings().redis_url)
    return _client


async def get_redis() -> AsyncIterator[Redis]:
    yield get_redis_client()
