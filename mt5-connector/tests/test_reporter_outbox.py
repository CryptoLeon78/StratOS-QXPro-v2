import json
from datetime import UTC, datetime

import pytest

from connector.buffer import Buffer
from connector.reporter_outbox import enqueue_reporter_outbox_once


@pytest.mark.asyncio
async def test_reporter_outbox_is_read_only_and_deduplicates(tmp_path) -> None:
    outbox_dir = tmp_path / "ea-outbox"
    outbox_dir.mkdir()
    event_path = outbox_dir / "events.jsonl"
    event = {
        "batch_type": "execution",
        "account_login": "demo-1",
        "magic": 118231,
        "fills": [
            {
                "order_id": "order-1",
                "symbol": "EURUSD",
                "type": "BUY",
                "volume": 0.1,
                "requested_price": 1.1,
                "executed_price": 1.1001,
                "spread": 0.0002,
                "ts": "2026-08-28T12:00:00Z",
            }
        ],
    }
    original = json.dumps(event) + "\n"
    event_path.write_text(original, encoding="utf-8")
    buffer = Buffer(str(tmp_path / "buffer.sqlite"))
    await buffer.connect()
    assert await enqueue_reporter_outbox_once(buffer, str(outbox_dir), "demo-1", "connector-1") == 1
    assert await enqueue_reporter_outbox_once(buffer, str(outbox_dir), "demo-1", "connector-1") == 0
    assert event_path.read_text(encoding="utf-8") == original
    assert len(await buffer.due_batches(datetime.now(UTC), 10)) == 1
    await buffer.close()


@pytest.mark.asyncio
async def test_reporter_outbox_leaves_an_incomplete_last_line_for_the_next_poll(tmp_path) -> None:
    outbox_dir = tmp_path / "ea-outbox"
    outbox_dir.mkdir()
    event_path = outbox_dir / "events.jsonl"
    incomplete = '{"batch_type":"execution","account_login":"demo-1"'
    event_path.write_text(incomplete, encoding="utf-8")
    buffer = Buffer(str(tmp_path / "buffer.sqlite"))
    await buffer.connect()

    assert await enqueue_reporter_outbox_once(buffer, str(outbox_dir), "demo-1", "connector-1") == 0
    assert event_path.read_text(encoding="utf-8") == incomplete
    assert await buffer.due_batches(datetime.now(UTC), 10) == []
    await buffer.close()


@pytest.mark.asyncio
async def test_reporter_outbox_can_be_scoped_to_the_g12_filename(tmp_path) -> None:
    outbox_dir = tmp_path / "ea-outbox"
    outbox_dir.mkdir()
    event = {"batch_type": "ea_state", "account_login": "demo-1", "eas": []}
    (outbox_dir / "stratos_g12.jsonl").write_text(json.dumps(event) + "\n", encoding="utf-8")
    (outbox_dir / "another_campaign.jsonl").write_text(json.dumps(event) + "\n", encoding="utf-8")
    buffer = Buffer(str(tmp_path / "buffer.sqlite"))
    await buffer.connect()

    accepted = await enqueue_reporter_outbox_once(
        buffer, str(outbox_dir), "demo-1", "connector-1", "stratos_g12.jsonl"
    )

    assert accepted == 1
    assert len(await buffer.due_batches(datetime.now(UTC), 10)) == 1
    await buffer.close()


async def test_reporter_outbox_canonicalizes_ea_state_decimal_before_sealing(tmp_path) -> None:
    outbox_dir = tmp_path / "ea-outbox"
    outbox_dir.mkdir()
    event = {
        "batch_type": "ea_state",
        "account_login": "demo-1",
        "eas": [
            {
                "magic": 118231,
                "ea_version": "g12-reporter-v1.1",
                "mode": "DEMO",
                "autotrading": True,
                "schedule_filter": {},
                "news_windows": [],
                "sizing_pct": 100.0,
            }
        ],
    }
    (outbox_dir / "stratos_g12.jsonl").write_text(json.dumps(event) + "\n", encoding="utf-8")
    buffer = Buffer(str(tmp_path / "buffer.sqlite"))
    await buffer.connect()

    assert await enqueue_reporter_outbox_once(buffer, str(outbox_dir), "demo-1", "connector-1") == 1
    due = await buffer.due_batches(datetime.now(UTC), 1)
    assert json.loads(due[0].payload_json)["eas"][0]["sizing_pct"] == "100.0"
    await buffer.close()
