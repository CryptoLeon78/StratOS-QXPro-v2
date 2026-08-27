import contextlib
from datetime import UTC, datetime

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.dependencies import oauth2_scheme
from core.auth.jwt import decode_token
from core.auth.revocation import revoke_jti
from core.auth.schemas import LogoutRequest, RefreshRequest, TokenResponse
from core.auth.service import authenticate_user, issue_tokens, refresh_tokens
from core.config import Settings, get_settings
from core.db.base import get_session
from core.redis import get_redis

router = APIRouter(prefix="/auth", tags=["auth"])

_INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="credenciales invalidas",
    headers={"WWW-Authenticate": "Bearer"},
)
_INVALID_REFRESH = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="refresh token invalido o expirado",
    headers={"WWW-Authenticate": "Bearer"},
)


@router.post("/token", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    user = await authenticate_user(session, form.username, form.password)
    if user is None:
        raise _INVALID_CREDENTIALS
    return await issue_tokens(user, settings, datetime.now(UTC))


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    redis: Redis = Depends(get_redis),
) -> TokenResponse:
    try:
        return await refresh_tokens(session, body.refresh_token, settings, datetime.now(UTC), redis)
    except jwt.InvalidTokenError as exc:
        raise _INVALID_REFRESH from exc


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: LogoutRequest,
    token: str = Depends(oauth2_scheme),
    settings: Settings = Depends(get_settings),
    redis: Redis = Depends(get_redis),
) -> None:
    """Revoca el access token actual + el refresh si se manda -- cierre de
    sesion real (G9), no solo "dejar de usar el token" (ver
    ASSUMPTIONS G5-07)."""
    try:
        access_payload = decode_token(token, settings)
    except jwt.InvalidTokenError as exc:
        raise _INVALID_CREDENTIALS from exc
    now = datetime.now(UTC)
    await revoke_jti(redis, access_payload.jti, access_payload.exp, now)
    if body.refresh_token:
        with contextlib.suppress(jwt.InvalidTokenError):
            refresh_payload = decode_token(body.refresh_token, settings)
            await revoke_jti(redis, refresh_payload.jti, refresh_payload.exp, now)
