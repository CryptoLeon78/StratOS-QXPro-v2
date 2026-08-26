"""Fixture compartida por los tests de `core.auth.router`: un
`httpx.AsyncClient` real contra la app FastAPI completa (`core.main.app`),
con `get_session` apuntado a `stratos_test` (mismo patron SAVEPOINT que
`db_session`) y `get_settings` fijado a un JWT_SECRET conocido -- sin tocar
el `.env` real. Mismo patron que `tests/ingest/conftest.py`."""

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.config import Settings, get_settings
from core.db.base import get_session
from core.main import app

TEST_JWT_SECRET = "test-secret-at-least-32-bytes-long-for-hs256"


def _test_settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://u:p@localhost/db",
        app_database_url="postgresql+asyncpg://u:p@localhost/db",
        app_db_password="x",
        redis_url="redis://localhost/0",
        jwt_secret=TEST_JWT_SECRET,
        ingest_api_keys="x",
    )  # type: ignore[call-arg]


@pytest_asyncio.fixture
async def auth_client(db_connection: AsyncConnection) -> AsyncIterator[AsyncClient]:
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
