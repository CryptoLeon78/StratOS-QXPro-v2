"""PARTE 12: poller. Usa `SimulatedMt5Client` (stratos-mt5-simulator, dev
dependency) en vez de mocks a mano -- ya es Mt5ClientProtocol-conformant y
determinista."""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from ingest_seal.sealing import verify_batch_seal
from simulator.client import SimulatedMt5Client
from simulator.scenarios.huerfanos import build_huerfanos_timeline
from simulator.scenarios.posicion_sin_sl import build_posicion_sin_sl_timeline

from connector.buffer import Buffer
from connector.poller import (
    poll_deals_incremental_once,
    poll_equity_once,
    poll_heartbeat_once,
    poll_positions_once,
    run_loop,
)

ACCOUNT_LOGIN = "100231"
CONNECTOR_ID = "conn-1"


@pytest.fixture
async def buffer(tmp_path: Path) -> Buffer:
    buf = Buffer(str(tmp_path / "outbox.sqlite"))
    await buf.connect()
    return buf


async def test_poll_positions_once_enqueues_a_verifiable_batch(buffer: Buffer) -> None:
    client = SimulatedMt5Client(build_posicion_sin_sl_timeline())
    await poll_positions_once(client, buffer, ACCOUNT_LOGIN, CONNECTOR_ID)

    due = await buffer.due_batches(datetime.now(UTC), limit=10)
    assert len(due) == 1
    assert due[0].batch_type == "positions"

    body = json.loads(due[0].payload_json)
    seal = body.pop("batch_sha256")
    verify_batch_seal(seal, ACCOUNT_LOGIN, "positions", [body])  # no debe lanzar
    assert len(body["positions"]) == 1
    assert body["positions"][0]["sl"] is None


async def test_poll_deals_incremental_persists_watermark_and_skips_empty(buffer: Buffer) -> None:
    client = SimulatedMt5Client(build_huerfanos_timeline())

    await poll_deals_incremental_once(client, buffer, ACCOUNT_LOGIN, CONNECTOR_ID)
    first_due = await buffer.due_batches(datetime.now(UTC), limit=10)
    assert len(first_due) == 1
    assert first_due[0].batch_type == "trades"
    watermark = await buffer.get_meta("last_deal_ts")
    assert watermark is not None

    await buffer.mark_sent(first_due[0].id)
    # el escenario no tiene deals nuevos tras el watermark -> no encola nada
    await poll_deals_incremental_once(client, buffer, ACCOUNT_LOGIN, CONNECTOR_ID)
    second_due = await buffer.due_batches(datetime.now(UTC), limit=10)
    assert second_due == []


class _NoAccountClient(SimulatedMt5Client):
    def account_info(self) -> None:  # type: ignore[override]
        return None


async def test_poll_equity_once_skips_when_account_info_unavailable(buffer: Buffer) -> None:
    client = _NoAccountClient(build_posicion_sin_sl_timeline())
    await poll_equity_once(client, buffer, ACCOUNT_LOGIN, CONNECTOR_ID)
    due = await buffer.due_batches(datetime.now(UTC), limit=10)
    assert due == []


async def test_poll_equity_once_enqueues(buffer: Buffer) -> None:
    client = SimulatedMt5Client(build_posicion_sin_sl_timeline())
    await poll_equity_once(client, buffer, ACCOUNT_LOGIN, CONNECTOR_ID)

    due = await buffer.due_batches(datetime.now(UTC), limit=10)
    assert len(due) == 1
    assert due[0].batch_type == "equity"
    body = json.loads(due[0].payload_json)
    assert "equity" in body


async def test_poll_heartbeat_once_enqueues(buffer: Buffer) -> None:
    await poll_heartbeat_once(buffer, ACCOUNT_LOGIN, CONNECTOR_ID, latency_ms=42)
    due = await buffer.due_batches(datetime.now(UTC), limit=10)
    assert len(due) == 1
    assert due[0].batch_type == "heartbeat"
    body = json.loads(due[0].payload_json)
    assert body["latency_ms"] == 42


async def test_run_loop_isolates_failures_and_keeps_running() -> None:
    calls = 0

    async def flaky_poll_once() -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("fallo simulado del primer ciclo")

    task = asyncio.create_task(run_loop(0.01, "test", flaky_poll_once))
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert calls >= 2  # sobrevivio al fallo del primer ciclo y siguio llamando
