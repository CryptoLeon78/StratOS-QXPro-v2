import httpx
import pytest

from core.config import Settings
from core.db.enums import AlertLevel
from core.notifications.telegram import (
    TELEGRAM_FAILURES_TOTAL,
    TELEGRAM_SENT_TOTAL,
    TelegramConfig,
    send_telegram_message,
)

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

_UNCONFIGURED_SETTINGS = Settings(
    database_url="postgresql+asyncpg://u:p@localhost/db",
    app_database_url="postgresql+asyncpg://u:p@localhost/db",
    app_db_password="x",
    redis_url="redis://localhost/0",
    jwt_secret="x" * 32,
    ingest_api_keys="x",
)  # type: ignore[call-arg]

_FAST_CONFIG = TelegramConfig(max_retries=2, backoff_base_s=0.0)


def _counter_value(counter: object, **labels: str) -> float:
    return counter.labels(**labels)._value.get()  # type: ignore[attr-defined]


async def test_returns_true_on_200() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "test-bot-token" in str(request.url)
        return httpx.Response(200, json={"ok": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    sent_before = _counter_value(TELEGRAM_SENT_TOTAL, level="CRITICA", channel="telegram")
    result = await send_telegram_message(
        client, _SETTINGS, "hola", AlertLevel.CRITICA, _FAST_CONFIG
    )
    assert result is True
    sent_after = _counter_value(TELEGRAM_SENT_TOTAL, level="CRITICA", channel="telegram")
    assert sent_after == sent_before + 1
    await client.aclose()


async def test_retries_and_eventually_fails_on_5xx() -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(500)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    failures_before = _counter_value(TELEGRAM_FAILURES_TOTAL, level="SUAVE")
    result = await send_telegram_message(client, _SETTINGS, "hola", AlertLevel.SUAVE, _FAST_CONFIG)
    assert result is False
    assert calls["count"] == _FAST_CONFIG.max_retries
    assert _counter_value(TELEGRAM_FAILURES_TOTAL, level="SUAVE") == failures_before + 1
    await client.aclose()


async def test_network_error_is_captured_never_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no network", request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    result = await send_telegram_message(
        client, _SETTINGS, "hola", AlertLevel.CRITICA, _FAST_CONFIG
    )
    assert result is False
    await client.aclose()


async def test_unconfigured_token_returns_false_without_any_request() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        pytest.fail("no deberia llamarse sin token/chat_id configurados")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    result = await send_telegram_message(
        client, _UNCONFIGURED_SETTINGS, "hola", AlertLevel.CRITICA, _FAST_CONFIG
    )
    assert result is False
    await client.aclose()
