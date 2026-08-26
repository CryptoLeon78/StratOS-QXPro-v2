"""Dependencia FastAPI para el `httpx.AsyncClient` saliente (Telegram, PARTE
9.4). Un modulo propio -- no vive en `notifications/telegram.py` ni en
`ingest/router.py` -- para que cualquier router futuro que necesite salir a
un servicio externo lo reutilice, y para que los tests puedan sustituirlo
via `app.dependency_overrides` (mismo patron que `get_session`/`get_redis`)
con un `httpx.MockTransport` sin tocar la red real."""

from collections.abc import AsyncIterator

import httpx


async def get_http_client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient() as client:
        yield client
