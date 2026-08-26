from datetime import UTC, datetime

from core.auth.jwt import create_access_token, create_refresh_token
from core.config import Settings
from core.ws.auth import authenticate_ws

_SETTINGS = Settings(
    database_url="postgresql+asyncpg://u:p@localhost/db",
    app_database_url="postgresql+asyncpg://u:p@localhost/db",
    app_db_password="x",
    redis_url="redis://localhost/0",
    jwt_secret="test-secret-at-least-32-bytes-long-for-hs256",
    ingest_api_keys="x",
)  # type: ignore[call-arg]


class _FakeWebSocket:
    def __init__(self, token: str | None) -> None:
        self.query_params = {"token": token} if token is not None else {}


async def test_valid_access_token_returns_payload() -> None:
    token = create_access_token(
        user_id=1,
        email="ivan@stratos.local",
        role="operator",
        settings=_SETTINGS,
        now=datetime.now(UTC),
    )
    payload = await authenticate_ws(_FakeWebSocket(token), _SETTINGS)  # type: ignore[arg-type]
    assert payload is not None
    assert payload.email == "ivan@stratos.local"


async def test_missing_token_returns_none() -> None:
    payload = await authenticate_ws(_FakeWebSocket(None), _SETTINGS)  # type: ignore[arg-type]
    assert payload is None


async def test_garbage_token_returns_none() -> None:
    payload = await authenticate_ws(_FakeWebSocket("not-a-jwt"), _SETTINGS)  # type: ignore[arg-type]
    assert payload is None


async def test_refresh_token_is_rejected() -> None:
    token = create_refresh_token(
        user_id=1,
        email="ivan@stratos.local",
        role="operator",
        settings=_SETTINGS,
        now=datetime.now(UTC),
    )
    payload = await authenticate_ws(_FakeWebSocket(token), _SETTINGS)  # type: ignore[arg-type]
    assert payload is None
