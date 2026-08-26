"""PARTE 12: poller -- 4 cadencias independientes (positions/deals/equity/
heartbeat, PARTE 12: "polling posiciones 5s / deals incremental / equity
30s / heartbeat 60s"). Cada poll recoge datos del cliente MT5 (real o
simulado), construye el payload via `wire.py` (mismo `model_dump(mode=
"json")` que el servidor recompone), lo sella (`ingest_seal`) y lo encola
en el buffer -- NUNCA toca la red directamente, esa es responsabilidad de
`sender.py` (proxima unidad). `_loop` atrapa y loguea las excepciones de
cada ciclo: un fallo en un poller nunca debe tirar a los demas.

`latency_ms` de heartbeat lo recibe como parametro (no se mide aqui):
medir la latencia real conector->core-engine es responsabilidad de quien
hace el POST (`sender.py`), no de quien encola -- el poller de heartbeat
no toca la red. Diseno propio, ver ASSUMPTIONS G4."""

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from ingest_seal.sealing import compute_batch_sha256

from connector.buffer import Buffer
from connector.protocol import Mt5ClientProtocol
from connector.wire import (
    WireHeartbeatRequest,
    WirePositionsRequest,
    WireTradesRequest,
    account_to_equity_request,
    deal_to_wire,
    position_to_wire,
)

logger = logging.getLogger(__name__)

_EPOCH = datetime(2000, 1, 1, tzinfo=UTC)


def _seal_and_serialize(account_login: str, batch_type: str, record: dict[str, object]) -> str:
    seal = compute_batch_sha256(account_login, batch_type, [record])
    return json.dumps({**record, "batch_sha256": seal})


async def poll_positions_once(
    client: Mt5ClientProtocol, buffer: Buffer, account_login: str, connector_instance_id: str
) -> None:
    positions = [position_to_wire(p) for p in client.positions_get()]
    request = WirePositionsRequest(
        account_login=account_login,
        connector_instance_id=connector_instance_id,
        ts=datetime.now(UTC),
        positions=positions,
    )
    record = request.model_dump(mode="json")
    await buffer.enqueue("positions", _seal_and_serialize(account_login, "positions", record))


async def poll_deals_once(
    client: Mt5ClientProtocol,
    buffer: Buffer,
    account_login: str,
    connector_instance_id: str,
    date_from: datetime,
    date_to: datetime,
) -> None:
    deals = [deal_to_wire(d) for d in client.history_deals_get(date_from, date_to)]
    if not deals:
        return
    request = WireTradesRequest(
        account_login=account_login, connector_instance_id=connector_instance_id, trades=deals
    )
    record = request.model_dump(mode="json")
    await buffer.enqueue("trades", _seal_and_serialize(account_login, "trades", record))


async def poll_deals_incremental_once(
    client: Mt5ClientProtocol, buffer: Buffer, account_login: str, connector_instance_id: str
) -> None:
    """El watermark (`last_deal_ts`) se persiste en `buffer.meta`, no en
    memoria: sobrevive a un reinicio del servicio (el conector no vuelve a
    pedir deals ya vistos tras un restart)."""
    watermark_str = await buffer.get_meta("last_deal_ts")
    date_from = datetime.fromisoformat(watermark_str) if watermark_str else _EPOCH
    date_to = datetime.now(UTC)
    await poll_deals_once(client, buffer, account_login, connector_instance_id, date_from, date_to)
    await buffer.set_meta("last_deal_ts", date_to.isoformat())


async def poll_equity_once(
    client: Mt5ClientProtocol, buffer: Buffer, account_login: str, connector_instance_id: str
) -> None:
    account = client.account_info()
    if account is None:
        return
    request = account_to_equity_request(
        account, account_login, connector_instance_id, datetime.now(UTC)
    )
    record = request.model_dump(mode="json")
    await buffer.enqueue("equity", _seal_and_serialize(account_login, "equity", record))


async def poll_heartbeat_once(
    buffer: Buffer, account_login: str, connector_instance_id: str, latency_ms: int
) -> None:
    request = WireHeartbeatRequest(
        connector_instance_id=connector_instance_id,
        account_login=account_login,
        latency_ms=latency_ms,
        ts=datetime.now(UTC),
    )
    record = request.model_dump(mode="json")
    await buffer.enqueue("heartbeat", _seal_and_serialize(account_login, "heartbeat", record))


async def run_loop(
    interval_s: float, task_name: str, poll_once: Callable[[], Awaitable[None]]
) -> None:
    """Bucle infinito: `poll_once` ya lleva sus argumentos ligados (via
    `functools.partial` o closure) para que este bucle sea generico entre
    las 4 cadencias."""
    while True:
        try:
            await poll_once()
        except Exception:
            logger.exception("poller %s fallo, se reintenta en el siguiente ciclo", task_name)
        await asyncio.sleep(interval_s)
