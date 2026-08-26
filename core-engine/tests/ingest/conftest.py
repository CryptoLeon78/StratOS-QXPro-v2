"""Fixture compartida por los tests de rutas de `core.ingest.router`: un
`httpx.AsyncClient` real contra la app FastAPI completa (`core.main.app`,
primer router del repo), con `get_session` apuntado a `stratos_test` (mismo
patron SAVEPOINT que `db_session`) y `get_settings` fijado a una API key
conocida -- sin tocar el `.env` real."""

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.config import Settings, get_settings
from core.db.base import get_session
from core.main import app

TEST_INGEST_API_KEY = "test-ingest-key"


def _test_settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://u:p@localhost/db",
        app_database_url="postgresql+asyncpg://u:p@localhost/db",
        app_db_password="x",
        redis_url="redis://localhost/0",
        jwt_secret="x",
        ingest_api_keys=TEST_INGEST_API_KEY,
    )


@pytest_asyncio.fixture
async def ingest_client(db_connection: AsyncConnection) -> AsyncIterator[AsyncClient]:
    async def _override_get_session() -> AsyncIterator[AsyncSession]:
        session = AsyncSession(
            bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        async with session:
            yield session

    app.dependency_overrides[get_session] = _override_get_session
    app.dependency_overrides[get_settings] = _test_settings
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.clear()
