"""Entrypoint del servicio: cablea buffer + poller (4 cadencias) + sender +
cliente MT5 real. NO VERIFICADO como servicio de verdad en esta sesion --
ni contra un terminal MT5 real (ver `real_adapter.py`) ni como servicio
NSSM real (ver `install_service.ps1`); solo se prueba que el cableado en
si no falla al arrancar (`tests/test_main.py`, con un cliente simulado y
un `core_engine_url` que nunca respondera con exito -- el sender loop
absorbe esos fallos, igual que haria un corte de red real)."""

import asyncio
import functools
import logging
from datetime import UTC, datetime

import httpx

from connector.buffer import Buffer
from connector.config import ConnectorSettings, get_connector_settings
from connector.http_client import BackoffConfig
from connector.poller import (
    poll_deals_incremental_once,
    poll_equity_once,
    poll_heartbeat_once,
    poll_positions_once,
    run_loop,
)
from connector.protocol import Mt5ClientProtocol
from connector.real_adapter import RealMt5Client
from connector.sender import drain_once

logger = logging.getLogger(__name__)


async def _get_or_create_connector_instance_id(buffer: Buffer) -> str:
    import uuid

    existing = await buffer.get_meta("connector_instance_id")
    if existing:
        return existing
    new_id = str(uuid.uuid4())
    await buffer.set_meta("connector_instance_id", new_id)
    return new_id


async def _run_sender_loop(
    client: httpx.AsyncClient, buffer: Buffer, api_key: str, backoff: BackoffConfig
) -> None:
    while True:
        try:
            await drain_once(client, buffer, api_key, backoff, datetime.now(UTC))
        except Exception:
            logger.exception("sender: fallo drenando el buffer, se reintenta")
        await asyncio.sleep(1.0)


async def run(mt5_client: Mt5ClientProtocol, settings: ConnectorSettings | None = None) -> None:
    settings = settings or get_connector_settings()
    buffer = Buffer(settings.buffer_db_path)
    await buffer.connect()
    connector_instance_id = await _get_or_create_connector_instance_id(buffer)

    backoff = BackoffConfig(
        base_seconds=settings.backoff_base_seconds,
        multiplier=settings.backoff_multiplier,
        max_seconds=settings.backoff_max_seconds,
    )

    if not mt5_client.initialize(path=settings.mt5_terminal_path):
        code, description = mt5_client.last_error()
        raise RuntimeError(f"MetaTrader5.initialize() fallo: {code} {description}")

    async with httpx.AsyncClient(base_url=settings.core_engine_url) as http_client:
        tasks = [
            asyncio.create_task(
                run_loop(
                    settings.positions_poll_interval_s,
                    "positions",
                    functools.partial(
                        poll_positions_once,
                        mt5_client,
                        buffer,
                        settings.account_login,
                        connector_instance_id,
                    ),
                )
            ),
            asyncio.create_task(
                run_loop(
                    settings.deals_poll_interval_s,
                    "deals",
                    functools.partial(
                        poll_deals_incremental_once,
                        mt5_client,
                        buffer,
                        settings.account_login,
                        connector_instance_id,
                    ),
                )
            ),
            asyncio.create_task(
                run_loop(
                    settings.equity_poll_interval_s,
                    "equity",
                    functools.partial(
                        poll_equity_once,
                        mt5_client,
                        buffer,
                        settings.account_login,
                        connector_instance_id,
                    ),
                )
            ),
            asyncio.create_task(
                run_loop(
                    settings.heartbeat_interval_s,
                    "heartbeat",
                    functools.partial(
                        poll_heartbeat_once,
                        buffer,
                        settings.account_login,
                        connector_instance_id,
                        0,
                    ),
                )
            ),
            asyncio.create_task(
                _run_sender_loop(http_client, buffer, settings.ingest_api_key, backoff)
            ),
        ]
        try:
            await asyncio.gather(*tasks)
        finally:
            for task in tasks:
                task.cancel()
            mt5_client.shutdown()
            await buffer.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run(RealMt5Client()))


if __name__ == "__main__":
    main()
