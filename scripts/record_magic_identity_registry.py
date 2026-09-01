"""Añade eventos G13 aprobados a un registro local JSONL append-only.

No abre MT5 ni modifica bases de datos. Requiere el hash exacto de la
propuesta y una referencia humana de aprobación antes de permitir ``--apply``.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from magic_identity import IdentityValidationError, sha256_payload, verify_payload_hash
from validate_magic_identity import validate_proposal


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposal", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--approval-ref", required=True)
    parser.add_argument(
        "--strategy-key", action="append", help="Limita el lote aprobado; repetible."
    )
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def _read_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
            verify_payload_hash(event)
        except (json.JSONDecodeError, IdentityValidationError) as error:
            raise SystemExit(f"registro corrupto en línea {number}") from error
        events.append(event)
    previous_hash: str | None = None
    for event in events:
        if event.get("prev_event_sha256") != previous_hash:
            raise SystemExit("registro con hash-chain inconsistente")
        previous_hash = str(event["payload_sha256"])
    return events


def _events_for_row(
    row: dict[str, Any], approval_ref: str, previous_hash: str | None
) -> list[dict[str, Any]]:
    base = {
        "schema_version": 1,
        "event_at_utc": datetime.now(UTC).isoformat(),
        "strategy_key": row["strategy_key"],
        "canonical_strategy_name": row["canonical_strategy_name"],
        "short_strategy_label": row["short_strategy_label"],
        "comment_identity": row["comment_identity"],
        "magic_number": row["magic_number"],
        "legacy_magic_numbers": row["legacy_magic_numbers"],
        "evidence": {
            "deployments": [
                {
                    key: deployment[key]
                    for key in ("account_login", "ea_sha256", "symbol", "timeframe")
                }
                for deployment in row["deployments"]
            ]
        },
        "accounts": row["accounts"],
        "operator_confirmation_ref": approval_ref,
        "proposal_payload_sha256": None,
    }
    events: list[dict[str, Any]] = []
    assigned = {**base, "event_type": "ASSIGNED", "prev_event_sha256": previous_hash}
    assigned["payload_sha256"] = sha256_payload(assigned)
    events.append(assigned)
    if row["legacy_magic_numbers"]:
        migration = {
            **base,
            "event_type": "MIGRATION_PLANNED",
            "prev_event_sha256": assigned["payload_sha256"],
        }
        migration["payload_sha256"] = sha256_payload(migration)
        events.append(migration)
    return events


def prepare_events(
    payload: dict[str, Any],
    existing: list[dict[str, Any]],
    approval_ref: str,
    selected_keys: set[str] | None,
) -> list[dict[str, Any]]:
    existing_assignments = {
        (str(event.get("strategy_key")), str(event.get("event_type"))) for event in existing
    }
    previous_hash = str(existing[-1]["payload_sha256"]) if existing else None
    events: list[dict[str, Any]] = []
    for row in payload["rows"]:
        if row["status"] != "PROPOSED":
            continue
        key = str(row["strategy_key"])
        if selected_keys is not None and key not in selected_keys:
            continue
        if (key, "ASSIGNED") in existing_assignments:
            continue
        row_events = _events_for_row(row, approval_ref, previous_hash)
        for event in row_events:
            event["proposal_payload_sha256"] = payload["payload_sha256"]
            event["prev_event_sha256"] = previous_hash
            event["payload_sha256"] = sha256_payload(
                {k: v for k, v in event.items() if k != "payload_sha256"}
            )
            previous_hash = event["payload_sha256"]
        events.extend(row_events)
    if selected_keys is not None:
        proposed = {
            str(row["strategy_key"]) for row in payload["rows"] if row["status"] == "PROPOSED"
        }
        unknown = selected_keys - proposed
        if unknown:
            raise IdentityValidationError(
                "strategy_key no propuesto: " + ", ".join(sorted(unknown))
            )
    return events


def main() -> None:
    args = parse_args()
    if not args.apply:
        raise SystemExit("BLOQUEADO: este comando exige --apply tras aprobación humana explícita")
    if not args.approval_ref.strip():
        raise SystemExit("BLOQUEADO: falta referencia de aprobación")
    proposal = json.loads(args.proposal.read_text(encoding="utf-8"))
    validate_proposal(proposal, args.policy)
    existing = _read_events(args.registry)
    selected = set(args.strategy_key) if args.strategy_key else None
    events = prepare_events(proposal, existing, args.approval_ref, selected)
    args.registry.parent.mkdir(parents=True, exist_ok=True)
    if events:
        with args.registry.open("a", encoding="utf-8", newline="\n") as handle:
            for event in events:
                handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    print(
        json.dumps(
            {"mode": "APPLY", "events_appended": len(events), "registry": str(args.registry)}
        )
    )


if __name__ == "__main__":
    main()
