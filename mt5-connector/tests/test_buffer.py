"""PARTE 12 (G4): buffer SQLite store-and-forward. TDD puro -- rojo
confirmado contra el stub `NotImplementedError` antes de implementar."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from connector.buffer import Buffer


@pytest.fixture
async def buffer(tmp_path: Path) -> Buffer:
    buf = Buffer(str(tmp_path / "outbox.sqlite"))
    await buf.connect()
    return buf


async def test_using_buffer_before_connect_raises(tmp_path: Path) -> None:
    buf = Buffer(str(tmp_path / "unconnected.sqlite"))
    with pytest.raises(RuntimeError, match="connect"):
        await buf.enqueue("trades", "{}")


async def test_enqueue_returns_increasing_ids(buffer: Buffer) -> None:
    first = await buffer.enqueue("trades", '{"a":1}')
    second = await buffer.enqueue("trades", '{"a":2}')
    assert second > first


async def test_enqueued_batch_is_immediately_due(buffer: Buffer) -> None:
    await buffer.enqueue("equity", '{"e":1}')
    due = await buffer.due_batches(datetime.now(UTC), limit=10)
    assert len(due) == 1
    assert due[0].batch_type == "equity"
    assert due[0].payload_json == '{"e":1}'
    assert due[0].attempts == 0


async def test_due_batches_respects_limit(buffer: Buffer) -> None:
    for i in range(5):
        await buffer.enqueue("heartbeat", f'{{"i":{i}}}')
    due = await buffer.due_batches(datetime.now(UTC), limit=3)
    assert len(due) == 3


async def test_mark_sent_removes_the_row(buffer: Buffer) -> None:
    row_id = await buffer.enqueue("trades", '{"a":1}')
    await buffer.mark_sent(row_id)
    due = await buffer.due_batches(datetime.now(UTC), limit=10)
    assert due == []


async def test_mark_failed_delays_next_attempt_and_keeps_the_row(buffer: Buffer) -> None:
    row_id = await buffer.enqueue("trades", '{"a":1}')
    now = datetime.now(UTC)
    future = now + timedelta(seconds=60)
    await buffer.mark_failed(row_id, "ConnectError", future)

    still_not_due = await buffer.due_batches(now, limit=10)
    assert still_not_due == []

    due_later = await buffer.due_batches(future + timedelta(seconds=1), limit=10)
    assert len(due_later) == 1
    assert due_later[0].attempts == 1


async def test_mark_failed_twice_increments_attempts(buffer: Buffer) -> None:
    row_id = await buffer.enqueue("trades", '{"a":1}')
    now = datetime.now(UTC)
    await buffer.mark_failed(row_id, "err1", now)
    await buffer.mark_failed(row_id, "err2", now)
    due = await buffer.due_batches(now, limit=10)
    assert due[0].attempts == 2


async def test_meta_round_trip(buffer: Buffer) -> None:
    assert await buffer.get_meta("connector_instance_id") is None
    await buffer.set_meta("connector_instance_id", "uuid-123")
    assert await buffer.get_meta("connector_instance_id") == "uuid-123"


async def test_meta_upsert_overwrites(buffer: Buffer) -> None:
    await buffer.set_meta("last_deal_ts", "2026-08-26T09:00:00Z")
    await buffer.set_meta("last_deal_ts", "2026-08-26T10:00:00Z")
    assert await buffer.get_meta("last_deal_ts") == "2026-08-26T10:00:00Z"


async def test_data_survives_reconnect(tmp_path: Path) -> None:
    path = str(tmp_path / "persist.sqlite")
    buf1 = Buffer(path)
    await buf1.connect()
    await buf1.enqueue("trades", '{"a":1}')
    await buf1.set_meta("connector_instance_id", "uuid-abc")
    await buf1.close()

    buf2 = Buffer(path)
    await buf2.connect()
    due = await buf2.due_batches(datetime.now(UTC), limit=10)
    assert len(due) == 1
    assert await buf2.get_meta("connector_instance_id") == "uuid-abc"
    await buf2.close()
