"""Cliente Redis compartido para el rate-limit (mismo patron que
core-engine/src/core/redis.py: singleton indexado por event loop en
curso, para que un cliente creado en un loop de test no se reutilice en
otro loop ya cerrado)."""

import asyncio
import weakref
from collections.abc import AsyncIterator

from redis.asyncio import Redis

from gateway.config import get_settings

_clients_by_loop: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, Redis]" = (
    weakref.WeakKeyDictionary()
)


def get_redis_client() -> Redis:
    loop = asyncio.get_running_loop()
    client = _clients_by_loop.get(loop)
    if client is None:
        client = Redis.from_url(get_settings().redis_url)
        _clients_by_loop[loop] = client
    return client


async def get_redis() -> AsyncIterator[Redis]:
    yield get_redis_client()
