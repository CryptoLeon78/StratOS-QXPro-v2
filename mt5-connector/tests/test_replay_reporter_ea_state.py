import json
from datetime import UTC, datetime

import pytest

from connector.buffer import Buffer
from connector.replay_reporter_ea_state import (
    append_audit_record,
    enqueue_replays,
    select_latest_ea_states,
)


def _state(magic: int, version: str) -> dict[str, object]:
    return {"batch_type": "ea_state", "account_login": "3000108092", "eas": [{
        "magic": magic, "ea_version": version, "mode": "REAL", "autotrading": True,
        "schedule_filter": {}, "news_windows": [], "sizing_pct": 0.2,
    }]}


@pytest.mark.asyncio
async def test_replay_selects_latest_requested_state_and_keeps_source_unchanged(tmp_path) -> None:
    outbox = tmp_path / "outbox"
    outbox.mkdir()
    source = outbox / "stratos_incubadora_295.jsonl"
    original = "\n".join([json.dumps(_state(295, "v1.1")), json.dumps(_state(295, "v1.3")), ""])
    source.write_text(original, encoding="utf-8")
    buffer = Buffer(str(tmp_path / "buffer.sqlite"))
    await buffer.connect()
    await buffer.set_meta("connector_instance_id", "connector-1")
    candidates = select_latest_ea_states(outbox, "*.jsonl", "3000108092", {295}, "connector-1")
    assert json.loads(candidates[0].payload_json)["eas"][0]["ea_version"] == "v1.3"
    assert source.read_text(encoding="utf-8") == original
    row_ids = await enqueue_replays(buffer, candidates)
    due = await buffer.due_batches(datetime.now(UTC), 10)
    assert row_ids == [due[0].id]
    assert due[0].batch_type == "ea_state"
    await buffer.close()


def test_replay_requires_every_explicit_magic(tmp_path) -> None:
    outbox = tmp_path / "outbox"
    outbox.mkdir()
    (outbox / "state.jsonl").write_text(json.dumps(_state(295, "v1.3")) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="243"):
        select_latest_ea_states(outbox, "*.jsonl", "3000108092", {243, 295}, "connector-1")


def test_replay_audit_is_append_only_and_excludes_payload(tmp_path) -> None:
    outbox = tmp_path / "outbox"
    outbox.mkdir()
    (outbox / "state.jsonl").write_text(json.dumps(_state(295, "v1.3")) + "\n", encoding="utf-8")
    candidates = select_latest_ea_states(outbox, "*.jsonl", "3000108092", {295}, "connector-1")
    audit_log = tmp_path / "audit" / "replays.jsonl"
    append_audit_record(
        audit_log,
        account_login="3000108092",
        reason="post_attachment_state_replay",
        candidates=candidates,
        row_ids=None,
    )
    record = json.loads(audit_log.read_text(encoding="utf-8"))
    assert record["applied"] is False
    assert record["replays"][0]["magic_number"] == 295
    assert "payload_json" not in json.dumps(record)
