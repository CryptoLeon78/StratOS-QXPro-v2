"""Fixture compartida por los tests de `core.routers.*`: un
`httpx.AsyncClient` real contra `core.main.app`, con `get_session`
apuntado a `stratos_test` (patron SAVEPOINT) y `get_current_user`
sustituido por un usuario de prueba fijo -- el flujo de auth JWT ya esta
probado end-to-end en tests/auth/, aqui basta con una identidad valida
inyectada via dependency_overrides (mismo patron que tests/ingest/
conftest.py para get_session/get_settings)."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.auth.dependencies import get_current_user
from core.config import Settings, get_settings
from core.db.base import get_session
from core.db.models.governance import User
from core.main import app

TEST_OPERATOR = User(
    id=1,
    email="operator@stratos.local",
    hashed_password="x",
    role="operator",
    created_at=datetime.now(UTC),
)


def _test_settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://u:p@localhost/db",
        app_database_url="postgresql+asyncpg://u:p@localhost/db",
        app_db_password="x",
        redis_url="redis://localhost/0",
        jwt_secret="test-secret-at-least-32-bytes-long-for-hs256",
        ingest_api_keys="x",
    )  # type: ignore[call-arg]


async def _override_get_current_user() -> User:
    return TEST_OPERATOR


@pytest_asyncio.fixture
async def api_client(db_connection: AsyncConnection) -> AsyncIterator[AsyncClient]:
    async def _override_get_session() -> AsyncIterator[AsyncSession]:
        session = AsyncSession(
            bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        async with session:
            yield session

    app.dependency_overrides[get_session] = _override_get_session
    app.dependency_overrides[get_settings] = _test_settings
    app.dependency_overrides[get_current_user] = _override_get_current_user
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.clear()
