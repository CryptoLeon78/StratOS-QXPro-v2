"""api-gateway (G9, PARTE 3/12): proxy transparente + rate-limit + WS
broker hacia core-engine. Sin logica de dominio -- ver proxy.py/
rate_limit.py/ws_proxy.py para el detalle de cada pieza; este modulo solo
ensambla FastAPI encima."""

from collections.abc import AsyncIterator

import httpx
import websockets
from fastapi import Depends, FastAPI, Request, Response, WebSocket, status
from redis.asyncio import Redis
from websockets.asyncio.client import ClientConnection
from websockets.exceptions import InvalidStatus

from gateway.config import Settings, get_settings
from gateway.http_client import get_http_client
from gateway.proxy import forward_request
from gateway.rate_limit import RateLimitExceeded, check_rate_limit
from gateway.redis_client import get_redis
from gateway.ws_proxy import bridge_frames

app = FastAPI(title="StratOS-QXPro api-gateway")

# Mismo set que proxy.py, mas content-encoding/content-length: httpx ya
# descomprimio el body en `.content`, reenviar esas 2 cabeceras del upstream
# tal cual no cuadraria con los bytes que de verdad se devuelven.
_EXCLUDED_RESPONSE_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "content-encoding",
    "content-length",
}


@app.get("/health", tags=["ops"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "api-gateway"}


def _client_ip(request: Request) -> str:
    """Detras de nginx (perfil prod, G9) el remoto real viene en
    X-Real-IP/X-Forwarded-For (infra/nginx/nginx.conf ya los fija); en dev,
    sin nginx delante, se usa la conexion directa."""
    forwarded = request.headers.get("x-real-ip") or request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_all(
    path: str,
    request: Request,
    settings: Settings = Depends(get_settings),
    client: httpx.AsyncClient = Depends(get_http_client),
    redis: Redis = Depends(get_redis),
) -> Response:
    try:
        await check_rate_limit(redis, _client_ip(request), settings.rate_limit_per_minute)
    except RateLimitExceeded as exc:
        return Response(content=str(exc), status_code=status.HTTP_429_TOO_MANY_REQUESTS)

    upstream = await forward_request(
        method=request.method,
        path=path,
        query=request.url.query,
        headers=dict(request.headers),
        body=await request.body(),
        client=client,
        upstream_base_url=settings.core_engine_url,
    )
    response_headers = {
        key: value
        for key, value in upstream.headers.items()
        if key.lower() not in _EXCLUDED_RESPONSE_HEADERS
    }
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=upstream.headers.get("content-type"),
    )


class _TextOnlyUpstream:
    """Adaptador entre `websockets.ClientConnection` (que puede recibir
    texto o binario) y `ws_proxy.UpstreamSocket` (solo texto): los 4
    topics de core-engine solo publican JSON como texto (ver
    `ws/bridge.py`) -- un frame binario ahi seria un bug del backend, no
    algo que este proxy deba silenciar en vez de fallar ruidoso."""

    def __init__(self, connection: ClientConnection) -> None:
        self._connection = connection

    async def send(self, data: str) -> None:
        await self._connection.send(data)

    def __aiter__(self) -> AsyncIterator[str]:
        return self._iter_text()

    async def _iter_text(self) -> AsyncIterator[str]:
        async for message in self._connection:
            if not isinstance(message, str):
                raise TypeError("frame binario inesperado desde core-engine WS")
            yield message


@app.websocket("/ws/{topic}")
async def proxy_ws(
    websocket: WebSocket, topic: str, settings: Settings = Depends(get_settings)
) -> None:
    await websocket.accept()
    upstream_url = f"{settings.core_engine_ws_url}/ws/{topic}"
    if websocket.url.query:
        upstream_url = f"{upstream_url}?{websocket.url.query}"
    try:
        async with websockets.connect(upstream_url) as upstream_ws:
            await bridge_frames(websocket, _TextOnlyUpstream(upstream_ws))
    except InvalidStatus:
        # core-engine rechazo el handshake (token invalido, ver ws/auth.py)
        # -- 1008 = policy violation, mismo codigo que core-engine ya usa.
        await websocket.close(code=1008)
