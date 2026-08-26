from datetime import UTC, datetime, timedelta

import jwt as pyjwt
import pytest

from core.auth.jwt import create_access_token, create_refresh_token, decode_token
from core.config import Settings


def _settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "database_url": "postgresql+asyncpg://u:p@localhost/db",
        "app_database_url": "postgresql+asyncpg://u:p@localhost/db",
        "app_db_password": "x",
        "redis_url": "redis://localhost/0",
        "jwt_secret": "test-secret-at-least-32-bytes-long-for-hs256",
        "ingest_api_keys": "x",
    }
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


def test_create_and_decode_access_token_roundtrips_claims() -> None:
    settings = _settings()
    now = datetime.now(UTC)
    token = create_access_token(
        user_id=7, email="ivan@example.com", role="operator", settings=settings, now=now
    )
    payload = decode_token(token, settings)
    assert payload.sub == 7
    assert payload.email == "ivan@example.com"
    assert payload.role == "operator"
    assert payload.type == "access"


def test_create_and_decode_refresh_token_has_type_refresh() -> None:
    settings = _settings()
    now = datetime.now(UTC)
    token = create_refresh_token(
        user_id=7, email="ivan@example.com", role="operator", settings=settings, now=now
    )
    payload = decode_token(token, settings)
    assert payload.type == "refresh"


def test_access_and_refresh_tokens_have_different_jti() -> None:
    settings = _settings()
    now = datetime.now(UTC)
    access = decode_token(
        create_access_token(
            user_id=1, email="a@a.com", role="operator", settings=settings, now=now
        ),
        settings,
    )
    refresh = decode_token(
        create_refresh_token(
            user_id=1, email="a@a.com", role="operator", settings=settings, now=now
        ),
        settings,
    )
    assert access.jti != refresh.jti


def test_decode_token_raises_on_expired_token() -> None:
    settings = _settings(jwt_access_ttl_min=1)
    long_ago = datetime.now(UTC) - timedelta(days=365)
    token = create_access_token(
        user_id=1, email="a@a.com", role="operator", settings=settings, now=long_ago
    )
    with pytest.raises(pyjwt.ExpiredSignatureError):
        decode_token(token, settings)


def test_decode_token_raises_on_bad_signature() -> None:
    settings = _settings()
    now = datetime.now(UTC)
    token = create_access_token(
        user_id=1, email="a@a.com", role="operator", settings=settings, now=now
    )
    header, payload, signature = token.split(".")
    # flipping un solo caracter del final del base64url no garantiza cambiar
    # los bytes decodificados (relleno de bits redundante) -- se sustituye un
    # tramo entero para asegurar una firma distinta de la real.
    tampered = f"{header}.{payload}.{'x' * len(signature)}"
    with pytest.raises(pyjwt.InvalidTokenError):
        decode_token(tampered, settings)
