"""Valida una entrega SQX→MQL5 contra un registro G13, sin compilar ni adjuntar.

El input describe una entrega ya preparada. Este comando sólo emite un
manifiesto sellado cuando MagicNumber y CustomComment coinciden exactamente
con una asignación append-only vigente.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from magic_identity import (
    IdentityValidationError,
    build_comment_identity,
    load_policy,
    sha256_payload,
    verify_payload_hash,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delivery", required=True, type=Path)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def _current_assignments(path: Path) -> dict[str, dict[str, Any]]:
    assignments: dict[str, dict[str, Any]] = {}
    previous_hash: str | None = None
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
            verify_payload_hash(event)
        except (json.JSONDecodeError, IdentityValidationError) as error:
            raise SystemExit(f"registro inválido en línea {number}") from error
        if event.get("prev_event_sha256") != previous_hash:
            raise SystemExit("registro con hash-chain inconsistente")
        previous_hash = str(event["payload_sha256"])
        if event.get("event_type") == "ASSIGNED":
            assignments[str(event["strategy_key"])] = event
    return assignments


def validate_delivery(
    delivery: dict[str, Any], registry: dict[str, dict[str, Any]], policy_path: Path
) -> dict[str, Any]:
    policy = load_policy(policy_path)
    required = (
        "strategy_key",
        "magic_number",
        "custom_comment",
        "ea_sha256",
        "symbol",
        "timeframe",
    )
    if any(delivery.get(key) in (None, "") for key in required):
        raise IdentityValidationError("entrega sin identidad mínima")
    assignment = registry.get(str(delivery["strategy_key"]))
    if assignment is None:
        raise IdentityValidationError("strategy_key sin asignación G13 aprobada")
    magic = delivery["magic_number"]
    if not isinstance(magic, int) or magic != assignment["magic_number"]:
        raise IdentityValidationError("MagicNumber no coincide con la asignación")
    expected_comment = build_comment_identity(
        str(assignment["short_strategy_label"]), magic, policy
    )
    if (
        delivery["custom_comment"] != expected_comment
        or assignment["comment_identity"] != expected_comment
    ):
        raise IdentityValidationError("CustomComment no coincide con MagicNumber registrado")
    evidence = assignment.get("evidence", {}).get("deployments", [])
    if not any(
        entry.get("ea_sha256") == delivery["ea_sha256"]
        and entry.get("symbol") == delivery["symbol"]
        and entry.get("timeframe") == delivery["timeframe"]
        for entry in evidence
    ):
        raise IdentityValidationError("hash, símbolo o timeframe no pertenecen a la asignación")
    return assignment


def main() -> None:
    args = parse_args()
    delivery = json.loads(args.delivery.read_text(encoding="utf-8"))
    assignment = validate_delivery(delivery, _current_assignments(args.registry), args.policy)
    result = {
        "schema_version": 1,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "mode": "VALIDATED_DELIVERY_ONLY",
        "strategy_key": assignment["strategy_key"],
        "magic_number": assignment["magic_number"],
        "comment_identity": assignment["comment_identity"],
        "delivery_sha256": sha256_payload(delivery),
        "assignment_payload_sha256": assignment["payload_sha256"],
    }
    result["payload_sha256"] = sha256_payload(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"valid": True, "output": str(args.output)}))


if __name__ == "__main__":
    main()
