"""Regenerate F7 queue sources after a SQX retest or MN rename.

This never contacts MT5 or changes the identity registry. It preserves the
currently deployed F7 magic and resolves the renamed SQX/MQL5 files through
the approved append-only identity assignment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from magic_identity import IdentityValidationError, verify_payload_hash


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def setup_window(sqx_path: Path) -> tuple[str, str]:
    try:
        with zipfile.ZipFile(sqx_path) as archive:
            content = archive.read("lastSettings.xml").decode("utf-8")
    except (KeyError, OSError, UnicodeDecodeError, zipfile.BadZipFile) as error:
        raise ValueError(f"SQX without readable lastSettings.xml: {sqx_path.name}") from error
    setup = re.search(r"<Setup\b[^>]*>", content)
    if setup is None:
        raise ValueError(f"SQX without Setup: {sqx_path.name}")
    start = re.search(r'dateFrom="([0-9]{4}\.[0-9]{2}\.[0-9]{2})"', setup.group(0))
    end = re.search(r'dateTo="([0-9]{4}\.[0-9]{2}\.[0-9]{2})"', setup.group(0))
    if start is None or end is None:
        raise ValueError(f"SQX without a retest window: {sqx_path.name}")
    return start.group(1).replace(".", "-"), end.group(1).replace(".", "-")


def current_assignments(path: Path) -> list[dict[str, Any]]:
    assignments: list[dict[str, Any]] = []
    previous_hash: str | None = None
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
            verify_payload_hash(event)
        except (json.JSONDecodeError, IdentityValidationError) as error:
            raise ValueError(f"invalid identity registry line {number}") from error
        if event.get("prev_event_sha256") != previous_hash:
            raise ValueError("identity registry hash-chain is inconsistent")
        previous_hash = str(event["payload_sha256"])
        if event.get("event_type") == "ASSIGNED":
            assignments.append(event)
    return assignments


def assignment_for(
    assignments: list[dict[str, Any]], account_login: str, legacy_magic: int
) -> dict[str, Any] | None:
    matches = [
        assignment
        for assignment in assignments
        if legacy_magic in {int(value) for value in assignment.get("legacy_magic_numbers", [])}
        and any(
            str(deployment.get("account_login")) == account_login
            for deployment in assignment.get("evidence", {}).get("deployments", [])
        )
    ]
    if len(matches) > 1:
        raise ValueError(f"ambiguous MN assignment: account={account_login} magic={legacy_magic}")
    return matches[0] if matches else None


def unique_source(source_root: Path, comment_identity: str, suffix: str) -> Path | None:
    matches = list(source_root.rglob(f"{comment_identity}{suffix}"))
    return matches[0] if len(matches) == 1 else None


def refresh_entry(
    entry: dict[str, Any], assignments: list[dict[str, Any]], source_root: Path,
    expected_from: str, expected_to: str,
) -> dict[str, Any]:
    refreshed = dict(entry)
    refreshed["source_refresh"] = {
        "at_utc": datetime.now(UTC).isoformat(),
        "expected_from": expected_from,
        "expected_to": expected_to,
    }
    if entry.get("status") != "READY_FOR_TICK_BACKTEST":
        return refreshed
    magic = entry.get("magic_number")
    if magic is None:
        refreshed["status"] = "WITHHELD_SOURCE_IDENTITY"
        return refreshed
    assignment = assignment_for(assignments, str(entry["account_login"]), int(magic))
    if assignment is None:
        refreshed["status"] = "WITHHELD_SOURCE_IDENTITY"
        return refreshed
    comment = str(assignment["comment_identity"])
    sqx = unique_source(source_root, comment, ".sqx")
    mq5 = unique_source(source_root, comment, ".mq5")
    if sqx is None or mq5 is None:
        refreshed["status"] = "WITHHELD_SOURCE_IDENTITY"
        return refreshed
    actual_from, actual_to = setup_window(sqx)
    if (actual_from, actual_to) != (expected_from, expected_to):
        refreshed["status"] = "WITHHELD_SOURCE_WINDOW"
        refreshed["source_refresh"].update({"actual_from": actual_from, "actual_to": actual_to})
        return refreshed
    refreshed.update(
        {
            "sqx_path": str(sqx),
            "mq5_path": str(mq5),
            "sqx_sha256": sha256(sqx),
            "mq5_sha256": sha256(mq5),
            "planned_magic_number": assignment["magic_number"],
            "planned_comment_identity": comment,
            "status": "READY_FOR_TICK_BACKTEST",
        }
    )
    return refreshed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, action="append", required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--expected-from", required=True)
    parser.add_argument("--expected-to", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    assignments = current_assignments(args.registry)
    entries = [
        refresh_entry(entry, assignments, args.source_root, args.expected_from, args.expected_to)
        for queue_path in args.queue
        for entry in json.loads(queue_path.read_text(encoding="utf-8"))["entries"]
    ]
    payload: dict[str, Any] = {
        "schema_version": 1,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "source_queues_sha256": {str(path): sha256(path) for path in args.queue},
        "registry_sha256": sha256(args.registry),
        "expected_range": {"from": args.expected_from, "to": args.expected_to},
        "entries": entries,
    }
    payload["payload_sha256"] = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ready = sum(entry["status"] == "READY_FOR_TICK_BACKTEST" for entry in entries)
    print(json.dumps({"entries": len(entries), "ready": ready, "output": str(args.output)}))


if __name__ == "__main__":
    main()
