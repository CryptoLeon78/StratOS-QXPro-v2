from datetime import UTC, datetime

import fakeredis
import jwt as pyjwt
import pytest
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.jwt import create_access_token, create_refresh_token, decode_token
from core.auth.service import authenticate_user, issue_tokens, refresh_tokens
from core.config import Settings
from tests.factories import TEST_USER_PASSWORD, UserFactory


@pytest.fixture
def redis() -> Redis:
    return fakeredis.FakeAsyncRedis()  # type: ignore[no-any-return]


def _settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://u:p@localhost/db",
        app_database_url="postgresql+asyncpg://u:p@localhost/db",
        app_db_password="x",
        redis_url="redis://localhost/0",
        jwt_secret="test-secret-at-least-32-bytes-long-for-hs256",
        ingest_api_keys="x",
    )  # type: ignore[call-arg]


async def _persisted_user(session: AsyncSession) -> object:
    user = UserFactory()
    session.add(user)
    await session.commit()
    return user


async def test_authenticate_user_returns_user_on_correct_credentials(
    db_session: AsyncSession,
) -> None:
    user = await _persisted_user(db_session)
    result = await authenticate_user(db_session, user.email, TEST_USER_PASSWORD)  # type: ignore[attr-defined]
    assert result is not None
    assert result.id == user.id  # type: ignore[attr-defined]


async def test_authenticate_user_returns_none_on_wrong_password(db_session: AsyncSession) -> None:
    user = await _persisted_user(db_session)
    result = await authenticate_user(db_session, user.email, "wrong-password")  # type: ignore[attr-defined]
    assert result is None


async def test_authenticate_user_returns_none_on_unknown_email(db_session: AsyncSession) -> None:
    result = await authenticate_user(db_session, "nobody@stratos.local", "whatever")
    assert result is None


async def test_issue_tokens_roundtrips_to_the_same_user(db_session: AsyncSession) -> None:
    user = await _persisted_user(db_session)
    settings = _settings()
    now = datetime.now(UTC)
    response = await issue_tokens(user, settings, now)  # type: ignore[arg-type]
    access_payload = decode_token(response.access_token, settings)
    assert access_payload.sub == user.id  # type: ignore[attr-defined]
    assert access_payload.email == user.email  # type: ignore[attr-defined]
    assert access_payload.type == "access"


async def test_refresh_tokens_issues_new_pair_for_valid_refresh_token(
    db_session: AsyncSession, redis: Redis
) -> None:
    user = await _persisted_user(db_session)
    settings = _settings()
    now = datetime.now(UTC)
    refresh = create_refresh_token(
        user_id=user.id,  # type: ignore[attr-defined]
        email=user.email,  # type: ignore[attr-defined]
        role=user.role,  # type: ignore[attr-defined]
        settings=settings,
        now=now,
    )
    response = await refresh_tokens(db_session, refresh, settings, now, redis)
    new_access = decode_token(response.access_token, settings)
    assert new_access.sub == user.id  # type: ignore[attr-defined]


async def test_refresh_tokens_rejects_an_access_token(
    db_session: AsyncSession, redis: Redis
) -> None:
    user = await _persisted_user(db_session)
    settings = _settings()
    now = datetime.now(UTC)
    access = create_access_token(
        user_id=user.id,  # type: ignore[attr-defined]
        email=user.email,  # type: ignore[attr-defined]
        role=user.role,  # type: ignore[attr-defined]
        settings=settings,
        now=now,
    )
    with pytest.raises(pyjwt.InvalidTokenError):
        await refresh_tokens(db_session, access, settings, now, redis)


async def test_refresh_tokens_rejects_a_deleted_user(
    db_session: AsyncSession, redis: Redis
) -> None:
    settings = _settings()
    now = datetime.now(UTC)
    refresh = create_refresh_token(
        user_id=999_999, email="ghost@stratos.local", role="operator", settings=settings, now=now
    )
    with pytest.raises(pyjwt.InvalidTokenError):
        await refresh_tokens(db_session, refresh, settings, now, redis)


async def test_refresh_tokens_revokes_the_used_refresh_token_rotation(
    db_session: AsyncSession, redis: Redis
) -> None:
    """Rotacion con revocacion (ASSUMPTIONS G5-07, cerrado en G9): el
    refresh token ya usado queda inservible, un robo despues del primer
    uso legitimo no permite un segundo refresh."""
    user = await _persisted_user(db_session)
    settings = _settings()
    now = datetime.now(UTC)
    refresh = create_refresh_token(
        user_id=user.id,  # type: ignore[attr-defined]
        email=user.email,  # type: ignore[attr-defined]
        role=user.role,  # type: ignore[attr-defined]
        settings=settings,
        now=now,
    )
    await refresh_tokens(db_session, refresh, settings, now, redis)

    with pytest.raises(pyjwt.InvalidTokenError):
        await refresh_tokens(db_session, refresh, settings, now, redis)
