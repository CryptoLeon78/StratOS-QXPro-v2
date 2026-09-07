from datetime import datetime

import jwt
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.jwt import create_access_token, create_refresh_token, decode_token
from core.auth.revocation import is_revoked, revoke_jti
from core.auth.schemas import TokenResponse
from core.auth.security import hash_password, verify_password
from core.config import Settings
from core.db.models.governance import User


async def authenticate_user(session: AsyncSession, email: str, password: str) -> User | None:
    user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None or not verify_password(password, user.hashed_password):
        return None
    return user


async def issue_tokens(user: User, settings: Settings, now: datetime) -> TokenResponse:
    access = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        session_version=user.session_version,
        settings=settings,
        now=now,
    )
    refresh = create_refresh_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        session_version=user.session_version,
        settings=settings,
        now=now,
    )
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.jwt_access_ttl_min * 60,
    )


async def refresh_tokens(
    session: AsyncSession, refresh_token: str, settings: Settings, now: datetime, redis: Redis
) -> TokenResponse:
    """Rotacion CON revocacion (G9, cierra ASSUMPTIONS G5-07): el refresh
    token se revoca en cuanto se usa, un robo posterior al primer uso
    legitimo ya no sirve para pedir un par nuevo. Levanta
    jwt.InvalidTokenError para TODOS los fallos (tipo incorrecto, usuario
    borrado, token vencido, YA REVOCADO) -- mismo tipo que decode_token, un
    unico except en el router basta."""
    payload = decode_token(refresh_token, settings)
    if payload.type != "refresh":
        raise jwt.InvalidTokenError("token is not a refresh token")
    if await is_revoked(redis, payload.jti):
        raise jwt.InvalidTokenError("refresh token already used")
    user = (await session.execute(select(User).where(User.id == payload.sub))).scalar_one_or_none()
    if user is None:
        raise jwt.InvalidTokenError("user no longer exists")
    if payload.session_version != user.session_version:
        raise jwt.InvalidTokenError("session has been invalidated")
    tokens = await issue_tokens(user, settings, now)
    await revoke_jti(redis, payload.jti, payload.exp, now)
    return tokens


async def change_password(
    session: AsyncSession,
    user: User,
    current_password: str,
    new_password: str,
    minimum_password_length: int,
) -> bool:
    if len(new_password) < minimum_password_length or not verify_password(
        current_password, user.hashed_password
    ):
        return False
    user.hashed_password = hash_password(new_password)
    user.session_version += 1
    await session.commit()
    return True
