"""PARTE 9.4: enrutado de un `Alert` a Telegram segun nivel. CRITICA ->
inmediata. SUAVE -> inmediata o encolada para el digest diario
(`telegram_soft_digest_enabled`, thresholds.seed.json -- sin loader vivo
de SystemConfig todavia, mismo patron de defaults-como-invocabilidad que
el resto de G3/G5). INFO -> nunca sale a Telegram (solo panel, literal)."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import Settings
from core.db.enums import AlertLevel
from core.db.models.decisions import Alert
from core.notifications.telegram import TelegramConfig, send_telegram_message

_DIGEST_QUEUE_KEY = "telegram:digest:pending"


class _RedisLike(Protocol):
    """Posicional-only (`/`) a proposito: `redis.asyncio.Redis.rpush` real
    llama a su primer parametro `name` (no `key`) y es variadico -- sin el
    `/`, mypy compara nombres de parametro para el matching estructural del
    Protocol y `Redis` deja de conformar (descubierto al tipar `redis:
    Redis = Depends(get_redis)` en ingest/router.py, antes enmascarado por
    un `ctx["redis"]: Any` en jobs/tasks.py)."""

    async def rpush(self, key: str, value: str, /) -> object: ...


@dataclass(frozen=True)
class DispatchConfig:
    soft_digest_enabled: bool = True


async def dispatch_alert(
    client: httpx.AsyncClient,
    redis: _RedisLike,
    settings: Settings,
    alert: Alert,
    config: DispatchConfig | None = None,
    telegram_config: TelegramConfig | None = None,
) -> None:
    config = config or DispatchConfig()

    if alert.level == AlertLevel.INFO:
        return

    if alert.level == AlertLevel.SUAVE and config.soft_digest_enabled:
        payload = {
            "ts": datetime.now(UTC).isoformat(),
            "level": alert.level.value,
            "module": alert.module,
            "message": alert.message,
        }
        await redis.rpush(_DIGEST_QUEUE_KEY, json.dumps(payload))
        return

    await send_telegram_message(client, settings, alert.message, alert.level, telegram_config)


async def dispatch_new_alerts(
    session: AsyncSession,
    redis: _RedisLike,
    client: httpx.AsyncClient,
    settings: Settings,
    run_start: datetime,
) -> None:
    """Envia (o encola, segun nivel) cada `Alert` creado DURANTE este
    barrido/ingesta -- `ts >= run_start` distingue una alerta nueva de una
    ya existente que solo se actualizo (`resolved=True` nunca toca `ts`).
    Compartido por `jobs/tasks.py` (barridos periodicos) y
    `ingest/router.py::post_positions` (alerta P5 inline, criterio PARTE 16
    #12 exige Telegram en <60s, no puede esperar al proximo barrido)."""
    new_alerts = (await session.execute(select(Alert).where(Alert.ts >= run_start))).scalars().all()
    for alert in new_alerts:
        await dispatch_alert(client, redis, settings, alert)
