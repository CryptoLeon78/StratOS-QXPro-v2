from datetime import UTC, datetime

import httpx
import pytest

from core.config import Settings
from core.db.enums import AlertLevel
from core.db.models.decisions import Alert
from core.notifications.dispatch import DispatchConfig, dispatch_alert
from core.notifications.telegram import TelegramConfig

_SETTINGS = Settings(
    database_url="postgresql+asyncpg://u:p@localhost/db",
    app_database_url="postgresql+asyncpg://u:p@localhost/db",
    app_db_password="x",
    redis_url="redis://localhost/0",
    jwt_secret="x" * 32,
    ingest_api_keys="x",
    telegram_bot_token="test-bot-token",
    telegram_chat_id="12345",
)  # type: ignore[call-arg]

_FAST_TELEGRAM = TelegramConfig(max_retries=1, backoff_base_s=0.0)


def _alert(level: AlertLevel) -> Alert:
    return Alert(ts=datetime.now(UTC), level=level, module="test", message="mensaje de prueba")


class _FakeRedis:
    def __init__(self) -> None:
        self.pushed: list[str] = []

    async def rpush(self, key: str, value: str) -> None:
        assert key == "telegram:digest:pending"
        self.pushed.append(value)


async def test_critica_sends_immediately() -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(200, json={"ok": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    redis = _FakeRedis()
    await dispatch_alert(
        client, redis, _SETTINGS, _alert(AlertLevel.CRITICA), DispatchConfig(), _FAST_TELEGRAM
    )
    assert calls["count"] == 1
    assert redis.pushed == []
    await client.aclose()


async def test_suave_with_digest_enabled_queues_instead_of_sending() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        pytest.fail("SUAVE con digest activado no debe llamar a Telegram directo")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    redis = _FakeRedis()
    await dispatch_alert(
        client,
        redis,
        _SETTINGS,
        _alert(AlertLevel.SUAVE),
        DispatchConfig(soft_digest_enabled=True),
        _FAST_TELEGRAM,
    )
    assert len(redis.pushed) == 1
    await client.aclose()


async def test_suave_with_digest_disabled_sends_immediately() -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(200, json={"ok": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    redis = _FakeRedis()
    await dispatch_alert(
        client,
        redis,
        _SETTINGS,
        _alert(AlertLevel.SUAVE),
        DispatchConfig(soft_digest_enabled=False),
        _FAST_TELEGRAM,
    )
    assert calls["count"] == 1
    assert redis.pushed == []
    await client.aclose()


async def test_info_never_reaches_telegram() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        pytest.fail("INFO nunca debe llegar a Telegram (PARTE 9.4)")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    redis = _FakeRedis()
    await dispatch_alert(
        client, redis, _SETTINGS, _alert(AlertLevel.INFO), DispatchConfig(), _FAST_TELEGRAM
    )
    assert redis.pushed == []
    await client.aclose()
