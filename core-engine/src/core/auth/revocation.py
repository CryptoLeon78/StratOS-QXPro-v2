"""Denylist de JWT via Redis (G9, PARTE 10.1: "revocacion real de tokens
queda para G9-hardening", ver ASSUMPTIONS G5-07). `TokenPayload.jti`
(UUID4, `auth/jwt.py`) ya identifica cada token de forma unica -- una clave
`revoked:{jti}` con TTL = tiempo restante hasta su propio `exp` es
suficiente: nunca sobrevive mas que el token que revoca, y `decode_token`
ya rechaza por firma/expiry cualquier jti mas alla de eso."""

from datetime import datetime

from redis.asyncio import Redis


async def revoke_jti(redis: Redis, jti: str, exp: datetime, now: datetime) -> None:
    ttl_seconds = int((exp - now).total_seconds())
    if ttl_seconds <= 0:
        return
    await redis.setex(f"revoked:{jti}", ttl_seconds, "1")


async def is_revoked(redis: Redis, jti: str) -> bool:
    return bool(await redis.exists(f"revoked:{jti}"))
