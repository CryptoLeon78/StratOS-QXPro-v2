import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt

from core.config import Settings

_ALGORITHM = "HS256"

TokenType = Literal["access", "refresh"]


@dataclass(frozen=True)
class TokenPayload:
    sub: int
    email: str
    role: str
    type: TokenType
    jti: str
    exp: datetime


def _create_token(
    *,
    user_id: int,
    email: str,
    role: str,
    token_type: TokenType,
    ttl: timedelta,
    settings: Settings,
    now: datetime,
) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "type": token_type,
        "jti": str(uuid.uuid4()),
        "exp": now + ttl,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def create_access_token(
    *, user_id: int, email: str, role: str, settings: Settings, now: datetime
) -> str:
    return _create_token(
        user_id=user_id,
        email=email,
        role=role,
        token_type="access",
        ttl=timedelta(minutes=settings.jwt_access_ttl_min),
        settings=settings,
        now=now,
    )


def create_refresh_token(
    *, user_id: int, email: str, role: str, settings: Settings, now: datetime
) -> str:
    return _create_token(
        user_id=user_id,
        email=email,
        role=role,
        token_type="refresh",
        ttl=timedelta(days=settings.jwt_refresh_ttl_days),
        settings=settings,
        now=now,
    )


def decode_token(token: str, settings: Settings) -> TokenPayload:
    """Levanta jwt.ExpiredSignatureError / jwt.InvalidTokenError si el
    token esta vencido o es invalido -- el caller (dependency FastAPI) lo
    traduce a 401."""
    decoded = jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
    return TokenPayload(
        sub=int(decoded["sub"]),
        email=decoded["email"],
        role=decoded["role"],
        type=decoded["type"],
        jti=decoded["jti"],
        exp=datetime.fromtimestamp(decoded["exp"], tz=UTC),
    )
