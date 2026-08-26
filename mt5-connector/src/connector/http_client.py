"""PARTE 12: backoff exponencial (solo el cap de 5 min es contractual;
base/multiplicador son asuncion propia -- ver `ConnectorSettings` y
ASSUMPTIONS G4) + POST sellado con `X-API-Key`. Sin logica de reintento
aqui: `sender.py` (proxima unidad) es quien orquesta reintentos via
`buffer.mark_failed`."""

from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class BackoffConfig:
    base_seconds: float
    multiplier: float
    max_seconds: float


def next_delay(attempts: int, config: BackoffConfig) -> float:
    return min(config.base_seconds * (config.multiplier**attempts), config.max_seconds)


async def send_batch(
    client: httpx.AsyncClient, url: str, api_key: str, payload_json: str
) -> httpx.Response:
    return await client.post(
        url,
        content=payload_json,
        headers={"X-API-Key": api_key, "Content-Type": "application/json"},
    )
