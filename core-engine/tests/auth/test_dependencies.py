from collections.abc import AsyncIterator
from datetime import UTC, datetime

import fakeredis
import pytest_asyncio
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.auth.dependencies import get_current_user
from core.auth.jwt import create_access_token, create_refresh_token, decode_token
from core.auth.revocation import revoke_jti
from core.config import Settings, get_settings
from core.db.base import get_session
from core.db.models.governance import User
from core.redis import get_redis
from tests.factories import UserFactory

_TEST_SETTINGS = Settings(
    database_url="postgresql+asyncpg://u:p@localhost/db",
    app_database_url="postgresql+asyncpg://u:p@localhost/db",
    app_db_password="x",
    redis_url="redis://localhost/0",
    jwt_secret="test-secret-at-least-32-bytes-long-for-hs256",
    ingest_api_keys="x",
)  # type: ignore[call-arg]

_app = FastAPI()


@_app.get("/protected")
async def _protected(user: User = Depends(get_current_user)) -> dict[str, str]:
    return {"email": user.email}


@pytest_asyncio.fixture
async def redis() -> Redis:
    return fakeredis.FakeAsyncRedis()  # type: ignore[no-any-return]


@pytest_asyncio.fixture
async def client(db_connection: AsyncConnection, redis: Redis) -> AsyncIterator[AsyncClient]:
    async def _override_get_session() -> AsyncIterator[AsyncSession]:
        session = AsyncSession(
            bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        async with session:
            yield session

    async def _override_get_redis() -> AsyncIterator[Redis]:
        yield redis

    _app.dependency_overrides[get_session] = _override_get_session
    _app.dependency_overrides[get_settings] = lambda: _TEST_SETTINGS
    _app.dependency_overrides[get_redis] = _override_get_redis
    try:
        async with AsyncClient(transport=ASGITransport(app=_app), base_url="http://test") as ac:
            yield ac
    finally:
        _app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def persisted_user(db_connection: AsyncConnection) -> User:
    session = AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    user = UserFactory()
    session.add(user)
    await session.commit()
    return user


async def test_protected_route_rejects_missing_token(client: AsyncClient) -> None:
    response = await client.get("/protected")
    assert response.status_code == 401


async def test_protected_route_rejects_invalid_token(client: AsyncClient) -> None:
    response = await client.get("/protected", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


async def test_protected_route_rejects_a_refresh_token(
    client: AsyncClient, persisted_user: User
) -> None:
    refresh = create_refresh_token(
        user_id=persisted_user.id,
        email=persisted_user.email,
        role=persisted_user.role,
        settings=_TEST_SETTINGS,
        now=datetime.now(UTC),
    )
    response = await client.get("/protected", headers={"Authorization": f"Bearer {refresh}"})
    assert response.status_code == 401


async def test_protected_route_accepts_a_valid_access_token(
    client: AsyncClient, persisted_user: User
) -> None:
    access = create_access_token(
        user_id=persisted_user.id,
        email=persisted_user.email,
        role=persisted_user.role,
        settings=_TEST_SETTINGS,
        now=datetime.now(UTC),
    )
    response = await client.get("/protected", headers={"Authorization": f"Bearer {access}"})
    assert response.status_code == 200
    assert response.json() == {"email": persisted_user.email}


async def test_protected_route_rejects_a_revoked_access_token(
    client: AsyncClient, persisted_user: User, redis: Redis
) -> None:
    now = datetime.now(UTC)
    access = create_access_token(
        user_id=persisted_user.id,
        email=persisted_user.email,
        role=persisted_user.role,
        settings=_TEST_SETTINGS,
        now=now,
    )
    payload = decode_token(access, _TEST_SETTINGS)
    await revoke_jti(redis, payload.jti, payload.exp, now)

    response = await client.get("/protected", headers={"Authorization": f"Bearer {access}"})
    assert response.status_code == 401
