from datetime import datetime

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.jwt import create_access_token, create_refresh_token, decode_token
from core.auth.schemas import TokenResponse
from core.auth.security import verify_password
from core.config import Settings
from core.db.models.governance import User


async def authenticate_user(session: AsyncSession, email: str, password: str) -> User | None:
    user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None or not verify_password(password, user.hashed_password):
        return None
    return user


async def issue_tokens(user: User, settings: Settings, now: datetime) -> TokenResponse:
    access = create_access_token(
        user_id=user.id, email=user.email, role=user.role, settings=settings, now=now
    )
    refresh = create_refresh_token(
        user_id=user.id, email=user.email, role=user.role, settings=settings, now=now
    )
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.jwt_access_ttl_min * 60,
    )


async def refresh_tokens(
    session: AsyncSession, refresh_token: str, settings: Settings, now: datetime
) -> TokenResponse:
    """Rotacion sin revocacion (ASSUMPTIONS G5: stateless, revocacion real
    de tokens queda para G9-hardening). Levanta jwt.InvalidTokenError para
    TODOS los fallos (tipo incorrecto, usuario borrado, token vencido) --
    mismo tipo que decode_token, un unico except en el router basta."""
    payload = decode_token(refresh_token, settings)
    if payload.type != "refresh":
        raise jwt.InvalidTokenError("token is not a refresh token")
    user = (await session.execute(select(User).where(User.id == payload.sub))).scalar_one_or_none()
    if user is None:
        raise jwt.InvalidTokenError("user no longer exists")
    return await issue_tokens(user, settings, now)
