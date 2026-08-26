"""Cliente Redis compartido para dependencias FastAPI (routers/*, WS) --
mismo patron singleton que `db/base.py::engine` (una conexion reutilizada,
no una nueva por request), pero indexado por event loop en curso: un
`redis.asyncio.Redis` creado en un loop no es valido en otro (asyncpg/redis
guardan primitivas internas atadas al loop que las creo). En produccion
(un unico loop de uvicorn durante toda la vida del proceso) esto degenera
al singleton puro; en tests, donde cada test de pytest-asyncio puede correr
en su propio loop, evita el "RuntimeError: Event loop is closed" de
reutilizar una conexion de un loop ya cerrado."""

import asyncio
import weakref
from collections.abc import AsyncIterator

from redis.asyncio import Redis

from core.config import get_settings

# WeakKeyDictionary: cuando un loop de test se cierra y se recolecta, su
# entrada (y el cliente Redis huerfano que le colgaba) se libera solo.
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
