from datetime import UTC, datetime

import fakeredis
import pytest

import core.auth.recovery as recovery_module
from core.auth.recovery import (
    _code_digest,
    _cooldown_key,
    _recovery_key,
    complete_recovery,
    recovery_is_configured,
    request_recovery_code,
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


class _ScalarResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object:
        return self._value


class _UserLookupSession:
    """Solo soporta el `select(User.id)...` que hace `request_recovery_code`."""

    def __init__(self, user_id: int | None) -> None:
        self._user_id = user_id

    async def execute(self, _statement: object) -> _ScalarResult:
        return _ScalarResult(self._user_id)


async def test_request_recovery_code_keeps_the_code_when_telegram_delivers(monkeypatch) -> None:
    settings = _settings()
    redis = fakeredis.FakeAsyncRedis()
    session = _UserLookupSession(user_id=1)
    delivered_to: list[str] = []

    async def _fake_send(_client, _settings, chat_id, _text, _config=None) -> bool:
        delivered_to.append(chat_id)
        return True

    monkeypatch.setattr(recovery_module, "send_telegram_direct_message", _fake_send)

    await request_recovery_code(session, redis, settings, settings.operator_email)

    assert delivered_to == [settings.telegram_recovery_chat_id]
    assert await redis.get(_recovery_key(settings.operator_email)) is not None
    assert await redis.exists(_cooldown_key(settings.operator_email))


async def test_request_recovery_code_discards_the_code_when_telegram_fails_to_deliver(
    monkeypatch,
) -> None:
    """Incidente 2026-09-26 (ver ASSUMPTIONS G13-65): si Telegram no entrega, el codigo
    generado no debe quedar vivo en Redis -- de lo contrario un `chat_id` mal configurado
    dejaria un codigo valido que nadie puede introducir a tiempo antes de que caduque."""
    settings = _settings()
    redis = fakeredis.FakeAsyncRedis()
    session = _UserLookupSession(user_id=1)

    async def _fake_send(*_args, **_kwargs) -> bool:
        return False

    monkeypatch.setattr(recovery_module, "send_telegram_direct_message", _fake_send)

    await request_recovery_code(session, redis, settings, settings.operator_email)

    assert await redis.get(_recovery_key(settings.operator_email)) is None
    assert not await redis.exists(_cooldown_key(settings.operator_email))


async def test_request_recovery_code_does_nothing_for_an_unregistered_email(monkeypatch) -> None:
    settings = _settings()
    redis = fakeredis.FakeAsyncRedis()
    session = _UserLookupSession(user_id=None)

    async def _fail_if_called(*_args, **_kwargs) -> bool:
        pytest.fail("no deberia intentar enviar sin un usuario registrado")

    monkeypatch.setattr(recovery_module, "send_telegram_direct_message", _fail_if_called)

    await request_recovery_code(session, redis, settings, settings.operator_email)

    assert await redis.get(_recovery_key(settings.operator_email)) is None


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
            None,
            redis,
            settings,
            email,
            "000000",
            "new-password-123",  # type: ignore[arg-type]
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
