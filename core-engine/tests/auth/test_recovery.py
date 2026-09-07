from datetime import UTC, datetime

import fakeredis

from core.auth.recovery import (
    _code_digest,
    _recovery_key,
    complete_recovery,
    recovery_is_configured,
)
from core.auth.security import hash_password, verify_password
from core.auth.service import change_password
from core.config import Settings
from core.db.models.governance import User


class _Result:
    def __init__(self, user: User) -> None:
        self._user = user

    def scalar_one_or_none(self) -> User:
        return self._user


class _Session:
    def __init__(self, user: User) -> None:
        self.user = user
        self.committed = False

    async def execute(self, _statement: object) -> _Result:
        return _Result(self.user)

    async def commit(self) -> None:
        self.committed = True


def _settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://u:p@localhost/db",
        app_database_url="postgresql+asyncpg://u:p@localhost/db",
        app_db_password="x",
        redis_url="redis://localhost/0",
        jwt_secret="test-secret-at-least-32-bytes-long-for-hs256",
        ingest_api_keys="x",
        operator_email="operator@stratos.local",
        telegram_bot_token="test-token",
        telegram_recovery_chat_id="test-private-chat",
    )  # type: ignore[call-arg]


def _user() -> User:
    return User(
        email="operator@stratos.local",
        hashed_password=hash_password("current-password"),
        role="operator",
        session_version=0,
        created_at=datetime.now(UTC),
    )


def test_recovery_requires_a_private_telegram_destination() -> None:
    settings = _settings()
    assert recovery_is_configured(settings)
    settings.telegram_recovery_chat_id = ""
    assert not recovery_is_configured(settings)


async def test_invalid_recovery_code_exhausts_the_one_time_code() -> None:
    settings = _settings()
    redis = fakeredis.FakeAsyncRedis()
    email = settings.operator_email
    key = _recovery_key(email)
    await redis.setex(key, settings.auth_recovery_code_ttl_s, _code_digest(settings, "123456"))

    for _ in range(settings.auth_recovery_max_attempts):
        completed = await complete_recovery(
            None, redis, settings, email, "000000", "new-password-123"  # type: ignore[arg-type]
        )
        assert not completed

    assert await redis.get(key) is None


async def test_valid_recovery_changes_the_hash_and_invalidates_old_sessions() -> None:
    settings = _settings()
    redis = fakeredis.FakeAsyncRedis()
    user = _user()
    session = _Session(user)
    code = "123456"
    await redis.setex(
        _recovery_key(user.email), settings.auth_recovery_code_ttl_s, _code_digest(settings, code)
    )

    completed = await complete_recovery(
        session, redis, settings, user.email, code, "new-password-123"
    )

    assert completed
    assert session.committed
    assert user.session_version == 1
    assert verify_password("new-password-123", user.hashed_password)
    assert await redis.get(_recovery_key(user.email)) is None


async def test_change_password_requires_the_current_password() -> None:
    user = _user()
    session = _Session(user)

    changed = await change_password(
        session, user, "wrong-password", "new-password-123", _settings().auth_password_min_length
    )

    assert not changed
    assert not session.committed
    assert user.session_version == 0


async def test_change_password_invalidates_previous_session_version() -> None:
    user = _user()
    session = _Session(user)

    changed = await change_password(
        session, user, "current-password", "new-password-123", _settings().auth_password_min_length
    )

    assert changed
    assert session.committed
    assert user.session_version == 1
