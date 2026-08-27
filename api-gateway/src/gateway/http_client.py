"""Dependencia FastAPI para el `httpx.AsyncClient` saliente hacia
core-engine (mismo patron que core-engine/src/core/http_client.py: un
cliente nuevo por request via `async with`, sustituible en tests con
`app.dependency_overrides` + `httpx.MockTransport` sin tocar la red real)."""

from collections.abc import AsyncIterator

import httpx


async def get_http_client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient() as client:
        yield client
