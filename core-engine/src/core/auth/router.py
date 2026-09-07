import contextlib
from datetime import UTC, datetime

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.dependencies import get_current_user, oauth2_scheme
from core.auth.jwt import decode_token
from core.auth.recovery import complete_recovery, recovery_is_configured, request_recovery_code
from core.auth.revocation import revoke_jti
from core.auth.schemas import (
    ChangePasswordRequest,
    LogoutRequest,
    RecoveryConfirmRequest,
    RecoveryRequest,
    RecoveryStatusResponse,
    RefreshRequest,
    TokenResponse,
)
from core.auth.service import authenticate_user, change_password, issue_tokens, refresh_tokens
from core.config import Settings, get_settings
from core.db.base import get_session
from core.db.models.governance import User
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
_INVALID_RECOVERY_CODE = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="codigo de recuperacion invalido o expirado",
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


@router.get("/recovery/status", response_model=RecoveryStatusResponse)
async def recovery_status(settings: Settings = Depends(get_settings)) -> RecoveryStatusResponse:
    return RecoveryStatusResponse(
        configured=recovery_is_configured(settings),
        minimum_password_length=settings.auth_password_min_length,
    )


@router.post("/recovery/request", status_code=status.HTTP_202_ACCEPTED)
async def request_password_recovery(
    body: RecoveryRequest,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> None:
    await request_recovery_code(session, redis, settings, body.email)


@router.post("/recovery/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_password_recovery(
    body: RecoveryConfirmRequest,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> None:
    completed = await complete_recovery(
        session, redis, settings, body.email, body.code, body.new_password
    )
    if not completed:
        raise _INVALID_RECOVERY_CODE


@router.post("/password", response_model=TokenResponse)
async def update_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    if not await change_password(
        session,
        user,
        body.current_password,
        body.new_password,
        settings.auth_password_min_length,
    ):
        raise _INVALID_CREDENTIALS
    return await issue_tokens(user, settings, datetime.now(UTC))


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
