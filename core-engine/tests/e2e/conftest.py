"""Fixtures de los tests end-to-end de los criterios PARTE 16 relevantes a
G5. Extiende el patron de `tests/ingest/conftest.py` (mismo `get_session`
apuntado a `stratos_test`) con `get_settings` fijado a credenciales de
Telegram DE PRUEBA (no reales -- ver comportamiento.md #7, nunca se toca
`.env`) y `get_http_client` sustituido por un `httpx.MockTransport` que
graba cada request en `telegram_calls`, para poder afirmar sin red real que
el aviso llego (criterio 12: "Posicion sin SL -> CRITICA + Telegram (mock)
<60 s")."""

from collections.abc import AsyncIterator

import httpx
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.config import Settings, get_settings
from core.db.base import get_session
from core.http_client import get_http_client
from core.main import app

TEST_INGEST_API_KEY = "test-ingest-key-e2e"


def _test_settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://u:p@localhost/db",
        app_database_url="postgresql+asyncpg://u:p@localhost/db",
        app_db_password="x",
        redis_url="redis://localhost/0",
        jwt_secret="x" * 32,
        ingest_api_keys=TEST_INGEST_API_KEY,
        telegram_bot_token="test-bot-token-e2e",
        telegram_chat_id="99999",
    )  # type: ignore[call-arg]


@pytest_asyncio.fixture
async def e2e_client_and_telegram_calls(
    db_connection: AsyncConnection,
) -> AsyncIterator[tuple[AsyncClient, list[httpx.Request]]]:
    telegram_calls: list[httpx.Request] = []

    def _telegram_handler(request: httpx.Request) -> httpx.Response:
        telegram_calls.append(request)
        return httpx.Response(200, json={"ok": True})

    async def _override_get_session() -> AsyncIterator[AsyncSession]:
        session = AsyncSession(
            bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        async with session:
            yield session

    async def _override_get_http_client() -> AsyncIterator[httpx.AsyncClient]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(_telegram_handler)) as client:
            yield client

    app.dependency_overrides[get_session] = _override_get_session
    app.dependency_overrides[get_settings] = _test_settings
    app.dependency_overrides[get_http_client] = _override_get_http_client
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client, telegram_calls
    finally:
        app.dependency_overrides.clear()
