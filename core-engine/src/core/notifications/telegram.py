"""PARTE 9.4: envio a Telegram con backoff exponencial (mismo criterio que
`mt5-connector/sender.py`, G4: reintentos con cap, NUNCA lanza -- "fallo
nunca bloquea la logica" es literal, el caller nunca depende del resultado
de esta funcion para continuar). Sin `TELEGRAM_BOT_TOKEN` y algun destino
configurados (Settings, ya existen), no hace ninguna peticion de red."""

import asyncio
from dataclasses import dataclass

import httpx
from prometheus_client import Counter

from core.config import Settings
from core.db.enums import AlertLevel

TELEGRAM_SENT_TOTAL = Counter(
    "telegram_sent_total", "Mensajes de Telegram enviados con exito", ["level", "channel"]
)
TELEGRAM_FAILURES_TOTAL = Counter(
    "telegram_failures_total", "Envios de Telegram agotados tras reintentos", ["level"]
)


@dataclass(frozen=True)
class TelegramConfig:
    max_retries: int = 3
    backoff_base_s: float = 2.0


def telegram_destinations(settings: Settings) -> tuple[str, ...]:
    """Return explicit multi-destination config or the legacy single destination."""
    configured = settings.telegram_chat_ids or settings.telegram_chat_id
    return tuple(
        dict.fromkeys(chat_id.strip() for chat_id in configured.split(",") if chat_id.strip())
    )


async def send_telegram_message(
    client: httpx.AsyncClient,
    settings: Settings,
    text: str,
    level: AlertLevel,
    config: TelegramConfig | None = None,
) -> bool:
    config = config or TelegramConfig()
    destinations = telegram_destinations(settings)
    if not settings.telegram_bot_token or not destinations:
        return False

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    delivered_to_all = True
    for chat_id in destinations:
        delivered = False
        for attempt in range(config.max_retries):
            try:
                response = await client.post(url, json={"chat_id": chat_id, "text": text})
                if response.status_code == 200:
                    TELEGRAM_SENT_TOTAL.labels(level=level.value, channel="telegram").inc()
                    delivered = True
                    break
            except httpx.HTTPError:
                pass
            if attempt < config.max_retries - 1:
                await asyncio.sleep(config.backoff_base_s * (2**attempt))
        if not delivered:
            TELEGRAM_FAILURES_TOTAL.labels(level=level.value).inc()
            delivered_to_all = False

    return delivered_to_all
