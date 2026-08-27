"""Rate limit por clave (IP del cliente, G9, PARTE 3/12): ventana fija de
60s sobre Redis (INCR+EXPIRE) -- suficiente para proteger core-engine de
un cliente descontrolado sin anadir una libreria de token-bucket nueva
cuando Redis ya es infra existente del proyecto."""

from redis.asyncio import Redis

_WINDOW_SECONDS = 60


class RateLimitExceeded(Exception):
    pass


async def check_rate_limit(redis: Redis, key: str, limit_per_minute: int) -> None:
    """Incrementa el contador de `key` para la ventana de 60s en curso.
    La primera peticion de la ventana fija el TTL; las siguientes solo
    incrementan. Lanza RateLimitExceeded al superar `limit_per_minute`."""
    redis_key = f"ratelimit:{key}"
    count = await redis.incr(redis_key)
    if count == 1:
        await redis.expire(redis_key, _WINDOW_SECONDS)
    if count > limit_per_minute:
        raise RateLimitExceeded(f"{key} superó {limit_per_minute} peticiones/min")
