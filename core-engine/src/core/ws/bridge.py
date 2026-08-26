"""PARTE 9.3: puente Redis Pub/Sub -> WebSocket. 8 topics, 4 endpoints (no
es 1:1) -- reenvia el JSON ya serializado por los publishers (`semaphore.py`/
`killswitch.py`/`pipeline.py`, G3; los nuevos de G5) tal cual, sin
transformarlo."""

from collections.abc import AsyncIterator

from redis.asyncio import Redis

TOPIC_MAP: dict[str, tuple[str, ...]] = {
    "/ws/equity": ("events:equity", "events:trade"),
    "/ws/alerts": ("events:alert", "events:decision"),
    "/ws/pipeline": ("events:pipeline", "events:semaphore", "events:killswitch"),
    "/ws/health": ("events:heartbeat",),
}


async def stream_topics(redis: Redis, topics: tuple[str, ...]) -> AsyncIterator[str]:
    pubsub = redis.pubsub()
    try:
        await pubsub.subscribe(*topics)
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = message["data"]
                yield data.decode("utf-8") if isinstance(data, bytes) else data
    finally:
        await pubsub.unsubscribe(*topics)
        await pubsub.aclose()  # type: ignore[no-untyped-call]
