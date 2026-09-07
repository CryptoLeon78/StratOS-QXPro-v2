"""Recuperacion con codigo temporal enviado al chat privado del operador."""

import hashlib
import hmac
import secrets
from math import ceil

import httpx
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.security import hash_password
from core.config import Settings
from core.db.models.governance import User
from core.notifications.telegram import send_telegram_direct_message

SECONDS_PER_MINUTE = 60


def _normalized_email(email: str) -> str:
    return email.strip().casefold()


def _email_key(email: str) -> str:
    return hashlib.sha256(_normalized_email(email).encode()).hexdigest()


def _code_digest(settings: Settings, code: str) -> str:
    return hmac.new(settings.jwt_secret.encode(), code.encode(), hashlib.sha256).hexdigest()


def _recovery_key(email: str) -> str:
    return f"auth:recovery:code:{_email_key(email)}"


def _attempts_key(email: str) -> str:
    return f"auth:recovery:attempts:{_email_key(email)}"


def _cooldown_key(email: str) -> str:
    return f"auth:recovery:cooldown:{_email_key(email)}"


def recovery_is_configured(settings: Settings) -> bool:
    return bool(
        settings.operator_email
        and settings.telegram_bot_token
        and settings.telegram_recovery_chat_id
    )


async def request_recovery_code(
    session: AsyncSession, redis: Redis, settings: Settings, email: str
) -> None:
    """No revela si el correo existe ni detalles de la configuracion."""
    normalized = _normalized_email(email)
    if (
        normalized != _normalized_email(settings.operator_email)
        or not recovery_is_configured(settings)
    ):
        return
    if await redis.exists(_cooldown_key(normalized)):
        return
    user_id = (
        await session.execute(select(User.id).where(User.email == normalized))
    ).scalar_one_or_none()
    if user_id is None:
        return
    code = str(secrets.randbelow(10**settings.auth_recovery_code_length)).zfill(
        settings.auth_recovery_code_length
    )
    await redis.setex(
        _recovery_key(normalized), settings.auth_recovery_code_ttl_s, _code_digest(settings, code)
    )
    await redis.setex(_cooldown_key(normalized), settings.auth_recovery_request_cooldown_s, "1")
    await redis.delete(_attempts_key(normalized))
    minutes = ceil(settings.auth_recovery_code_ttl_s / SECONDS_PER_MINUTE)
    text = settings.auth_recovery_telegram_template.format(code=code, minutes=minutes)
    async with httpx.AsyncClient(timeout=settings.auth_recovery_request_cooldown_s) as client:
        delivered = await send_telegram_direct_message(
            client, settings, settings.telegram_recovery_chat_id, text
        )
    if not delivered:
        await redis.delete(_recovery_key(normalized), _cooldown_key(normalized))


async def complete_recovery(
    session: AsyncSession,
    redis: Redis,
    settings: Settings,
    email: str,
    code: str,
    new_password: str,
) -> bool:
    normalized = _normalized_email(email)
    if (
        normalized != _normalized_email(settings.operator_email)
        or len(new_password) < settings.auth_password_min_length
    ):
        return False
    key = _recovery_key(normalized)
    stored = await redis.get(key)
    if stored is None:
        return False
    stored_digest = stored.decode() if isinstance(stored, bytes) else stored
    if not hmac.compare_digest(stored_digest, _code_digest(settings, code.strip())):
        attempts_key = _attempts_key(normalized)
        attempts = await redis.incr(attempts_key)
        if attempts == 1:
            await redis.expire(attempts_key, settings.auth_recovery_code_ttl_s)
        if attempts >= settings.auth_recovery_max_attempts:
            await redis.delete(key, attempts_key)
        return False
    user = (
        await session.execute(select(User).where(User.email == normalized))
    ).scalar_one_or_none()
    if user is None:
        return False
    user.hashed_password = hash_password(new_password)
    user.session_version += 1
    await session.commit()
    await redis.delete(key, _attempts_key(normalized))
    return True
