"""PARTE 12: sender -- drena el buffer y hace el POST real (`X-API-Key`,
via `http_client.send_batch`), aplicando backoff exponencial por fila
(`buffer.mark_failed`) en cada fallo transitorio. Es la unica pieza que
toca la red; `poller.py` solo encola. Junto con `buffer.enqueue`, es lo
que hace mecanicamente cierto el criterio de salida de G4 ("corte de 10
min sin perdidas ni duplicados"): durante el corte, `drain_once` sigue
fallando y reintentando con backoff creciente; el poller sigue encolando
sin bloquearse; al recuperarse la red, `drain_once` vacia el backlog en
orden -- cada payload ya sellado en el momento de encolar, asi que un
reintento nunca produce un lote distinto."""

import logging
from datetime import UTC, datetime, timedelta

import httpx

from connector.buffer import Buffer
from connector.http_client import BackoffConfig, next_delay, send_batch

logger = logging.getLogger(__name__)

# 429 (rate limit) y 5xx son transitorios -> reintentar con backoff. Otro
# 4xx (422 sello invalido, 404 cuenta desconocida, ...) es un lote mal
# formado que un reintento identico NUNCA arreglaria -- se descarta con
# log en vez de reintentar indefinidamente y bloquear el resto de la cola.
_RETRYABLE_STATUS = {429}


def _is_retryable(status_code: int) -> bool:
    return status_code in _RETRYABLE_STATUS or status_code >= 500


async def drain_once(
    client: httpx.AsyncClient,
    buffer: Buffer,
    api_key: str,
    backoff: BackoffConfig,
    now: datetime,
    limit: int = 20,
) -> int:
    """Un paso de drenaje: intenta enviar los lotes vencidos. Devuelve
    cuantos se enviaron con exito."""
    due = await buffer.due_batches(now, limit=limit)
    sent = 0
    for row in due:
        url = f"/ingest/{row.batch_type}"
        try:
            response = await send_batch(client, url, api_key, row.payload_json)
        except httpx.HTTPError as exc:
            delay = next_delay(row.attempts, backoff)
            await buffer.mark_failed(row.id, str(exc), datetime.now(UTC) + timedelta(seconds=delay))
            continue

        if response.status_code < 300:
            await buffer.mark_sent(row.id)
            sent += 1
        elif _is_retryable(response.status_code):
            delay = next_delay(row.attempts, backoff)
            await buffer.mark_failed(
                row.id,
                f"HTTP {response.status_code}",
                datetime.now(UTC) + timedelta(seconds=delay),
            )
        else:
            logger.error(
                "lote %s (id=%s) rechazado permanentemente: HTTP %s -- descartado, no se reintenta",
                row.batch_type,
                row.id,
                response.status_code,
            )
            await buffer.mark_sent(row.id)

    return sent
