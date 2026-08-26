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

from core.config import Settings
from core.db.enums import AlertLevel
from core.db.models.decisions import Alert
from core.notifications.telegram import TelegramConfig, send_telegram_message

_DIGEST_QUEUE_KEY = "telegram:digest:pending"


class _RedisLike(Protocol):
    async def rpush(self, key: str, value: str) -> object: ...


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
