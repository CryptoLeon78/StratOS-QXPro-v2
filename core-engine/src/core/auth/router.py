from datetime import UTC, datetime

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.schemas import RefreshRequest, TokenResponse
from core.auth.service import authenticate_user, issue_tokens, refresh_tokens
from core.config import Settings, get_settings
from core.db.base import get_session

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
) -> TokenResponse:
    try:
        return await refresh_tokens(session, body.refresh_token, settings, datetime.now(UTC))
    except jwt.InvalidTokenError as exc:
        raise _INVALID_REFRESH from exc
