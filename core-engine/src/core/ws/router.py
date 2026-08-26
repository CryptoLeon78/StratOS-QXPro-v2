"""PARTE 9.3: 4 endpoints WS (`/ws/equity`, `/ws/alerts`, `/ws/pipeline`,
`/ws/health`), cada uno reenviando su subconjunto de `TOPIC_MAP`
(`bridge.py`, ya existe). Token invalido/ausente -> `close(1008)` antes de
aceptar la conexion (Policy Violation, RFC 6455)."""

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis

from core.config import Settings, get_settings
from core.metrics import WS_CONNECTIONS_ACTIVE
from core.redis import get_redis
from core.ws.auth import authenticate_ws
from core.ws.bridge import TOPIC_MAP, stream_topics

router = APIRouter()

_POLICY_VIOLATION = 1008


async def _handle(websocket: WebSocket, path: str, settings: Settings, redis: Redis) -> None:
    payload = await authenticate_ws(websocket, settings)
    if payload is None:
        await websocket.close(code=_POLICY_VIOLATION)
        return

    await websocket.accept()
    WS_CONNECTIONS_ACTIVE.labels(channel=path).inc()
    try:
        async for message in stream_topics(redis, TOPIC_MAP[path]):
            await websocket.send_text(message)
    except WebSocketDisconnect:
        pass
    finally:
        WS_CONNECTIONS_ACTIVE.labels(channel=path).dec()


@router.websocket("/ws/equity")
async def ws_equity(
    websocket: WebSocket,
    settings: Settings = Depends(get_settings),
    redis: Redis = Depends(get_redis),
) -> None:
    await _handle(websocket, "/ws/equity", settings, redis)


@router.websocket("/ws/alerts")
async def ws_alerts(
    websocket: WebSocket,
    settings: Settings = Depends(get_settings),
    redis: Redis = Depends(get_redis),
) -> None:
    await _handle(websocket, "/ws/alerts", settings, redis)


@router.websocket("/ws/pipeline")
async def ws_pipeline(
    websocket: WebSocket,
    settings: Settings = Depends(get_settings),
    redis: Redis = Depends(get_redis),
) -> None:
    await _handle(websocket, "/ws/pipeline", settings, redis)


@router.websocket("/ws/health")
async def ws_health(
    websocket: WebSocket,
    settings: Settings = Depends(get_settings),
    redis: Redis = Depends(get_redis),
) -> None:
    await _handle(websocket, "/ws/health", settings, redis)
