import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.jwt import decode_token
from core.config import Settings, get_settings
from core.db.base import get_session
from core.db.models.governance import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="credenciales invalidas o expiradas",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> User:
    try:
        payload = decode_token(token, settings)
    except jwt.InvalidTokenError as exc:
        raise _UNAUTHORIZED from exc
    if payload.type != "access":
        raise _UNAUTHORIZED
    user = (await session.execute(select(User).where(User.id == payload.sub))).scalar_one_or_none()
    if user is None:
        raise _UNAUTHORIZED
    return user
