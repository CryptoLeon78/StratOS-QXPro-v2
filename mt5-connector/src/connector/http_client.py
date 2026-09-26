"""PARTE 12: backoff exponencial (solo el cap de 5 min es contractual;
base/multiplicador son asuncion propia -- ver `ConnectorSettings` y
ASSUMPTIONS G4) + POST sellado con `X-API-Key`. Sin logica de reintento
aqui: `sender.py` (proxima unidad) es quien orquesta reintentos via
`buffer.mark_failed`."""

import math
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class BackoffConfig:
    base_seconds: float
    multiplier: float
    max_seconds: float


def next_delay(attempts: int, config: BackoffConfig) -> float:
    """Retardo del intento `attempts`, acotado por `max_seconds`.

    El tope no puede aplicarse *despues* de exponenciar: `multiplier**attempts`
    se evalua entero antes de llegar al `min()`, y con suficientes intentos
    supera el rango del float (`OverflowError: Result too large`). Es lo que
    tumbo a los conectores del VPS el 2026-09-26 -- mientras el servidor no
    respondia, `attempts` crecia sin freno hasta que calcular el propio retardo
    empezo a lanzar la excepcion, y la cola dejo de drenarse.

    Se calcula antes a partir de que intento ya se alcanza el techo, y a partir
    de ahi se devuelve el techo sin exponenciar nada.
    """
    if attempts <= 0 or config.multiplier <= 1 or config.base_seconds <= 0:
        return min(config.base_seconds, config.max_seconds)
    intentos_hasta_el_techo = math.log(
        config.max_seconds / config.base_seconds, config.multiplier
    )
    if attempts >= intentos_hasta_el_techo:
        return config.max_seconds
    return min(config.base_seconds * (config.multiplier**attempts), config.max_seconds)


async def send_batch(
    client: httpx.AsyncClient, url: str, api_key: str, payload_json: str
) -> httpx.Response:
    return await client.post(
        url,
        content=payload_json,
        headers={"X-API-Key": api_key, "Content-Type": "application/json"},
    )
