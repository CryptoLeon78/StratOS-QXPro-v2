"""Controlled replay of sealed reporter EA state from an append-only JSONL.

This maintenance tool never opens MetaTrader, edits a reporter outbox, handles
an execution, or places an order. With ``--apply`` it only enqueues a newly
sealed ``ea_state`` snapshot in the connector's local SQLite buffer.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from connector.buffer import Buffer
from connector.poller import _seal_and_serialize
from connector.reporter_outbox import canonicalize_reporter_event


@dataclass(frozen=True)
class ReplayCandidate:
    """One selected EA state and its immutable source provenance."""

    magic_number: int
    source_path: Path
    source_line_sha256: str
    payload_json: str


def _complete_lines(path: Path) -> list[str]:
    raw_payload = path.read_text(encoding="utf-8")
    lines = raw_payload.splitlines()
    return lines if not raw_payload or raw_payload.endswith(("\n", "\r")) else lines[:-1]


def select_latest_ea_states(
    outbox_dir: Path,
    filename_pattern: str,
    account_login: str,
    magic_numbers: set[int],
    connector_instance_id: str,
) -> list[ReplayCandidate]:
    """Select exactly the latest complete state per requested magic.

    The source JSONL remains untouched. Each selected EA is resealed alone, so
    an unrelated candidate cannot be promoted as a side effect of recovery.
    """
    if not outbox_dir.is_dir():
        raise ValueError(f"reporter outbox directory does not exist: {outbox_dir}")
    if not filename_pattern or Path(filename_pattern).name != filename_pattern:
        raise ValueError("filename pattern must not contain a directory")
    if not magic_numbers:
        raise ValueError("at least one magic number is required")

    latest: dict[int, ReplayCandidate] = {}
    for source_path in sorted(outbox_dir.glob(filename_pattern)):
        for raw_line in _complete_lines(source_path):
            if not raw_line.strip():
                continue
            try:
                source_event = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            if (
                source_event.get("batch_type") != "ea_state"
                or source_event.get("account_login") != account_login
            ):
                continue
            eas = source_event.get("eas")
            if not isinstance(eas, list):
                continue
            for ea in eas:
                if not isinstance(ea, dict) or ea.get("magic") not in magic_numbers:
                    continue
                event: dict[str, object] = {"account_login": account_login, "eas": [ea]}
                normalized = canonicalize_reporter_event("ea_state", event)
                normalized["connector_instance_id"] = connector_instance_id
                payload_json = _seal_and_serialize(account_login, "ea_state", normalized)
                magic_number = int(ea["magic"])
                latest[magic_number] = ReplayCandidate(
                    magic_number=magic_number,
                    source_path=source_path,
                    source_line_sha256=hashlib.sha256(raw_line.encode("utf-8")).hexdigest(),
                    payload_json=payload_json,
                )
    missing = sorted(magic_numbers - set(latest))
    if missing:
        raise ValueError(f"no complete matching ea_state for magic numbers: {missing}")
    return [latest[magic] for magic in sorted(latest)]


async def enqueue_replays(buffer: Buffer, candidates: Sequence[ReplayCandidate]) -> list[int]:
    """Add explicit snapshots without deleting dedupe metadata or history."""
    return [await buffer.enqueue("ea_state", candidate.payload_json) for candidate in candidates]


def append_audit_record(
    audit_log: Path,
    *,
    account_login: str,
    reason: str,
    candidates: Sequence[ReplayCandidate],
    row_ids: Sequence[int] | None,
) -> None:
    audit_log.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "event_type": "REPORTER_EA_STATE_REPLAY",
        "occurred_at": datetime.now(UTC).isoformat(),
        "account_login": account_login,
        "reason": reason,
        "applied": row_ids is not None,
        "replays": [
            {
                "magic_number": candidate.magic_number,
                "source_path": str(candidate.source_path),
                "source_line_sha256": candidate.source_line_sha256,
                "payload_sha256": hashlib.sha256(
                    candidate.payload_json.encode("utf-8")
                ).hexdigest(),
                "buffer_row_id": None if row_ids is None else row_ids[index],
            }
            for index, candidate in enumerate(candidates)
        ],
    }
    with audit_log.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")


async def _run(args: argparse.Namespace) -> int:
    buffer = Buffer(args.buffer_db)
    await buffer.connect()
    try:
        connector_instance_id = await buffer.get_meta("connector_instance_id")
        if not connector_instance_id:
            raise ValueError("connector buffer has no connector_instance_id")
        candidates = select_latest_ea_states(
            Path(args.outbox_dir),
            args.outbox_filename,
            args.account_login,
            set(args.magic),
            connector_instance_id,
        )
        row_ids = await enqueue_replays(buffer, candidates) if args.apply else None
    finally:
        await buffer.close()
    append_audit_record(
        Path(args.audit_log),
        account_login=args.account_login,
        reason=args.reason,
        candidates=candidates,
        row_ids=row_ids,
    )
    print(
        json.dumps(
            {
                "status": "enqueued" if args.apply else "dry_run",
                "magic_numbers": [item.magic_number for item in candidates],
                "buffer_row_ids": row_ids,
                "audit_log": args.audit_log,
            },
            sort_keys=True,
        )
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outbox-dir", required=True)
    parser.add_argument("--outbox-filename", default="*.jsonl")
    parser.add_argument("--account-login", required=True)
    parser.add_argument("--buffer-db", required=True)
    parser.add_argument("--audit-log", required=True)
    parser.add_argument("--magic", type=int, action="append", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.reason.strip():
        parser.error("--reason must not be blank")
    return args


def main() -> None:
    raise SystemExit(asyncio.run(_run(parse_args())))


if __name__ == "__main__":
    main()
