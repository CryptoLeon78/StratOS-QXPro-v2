"""Assign a unique, globally segregated magic to every analysis-candidate EA.

The tool is deliberately scoped to research exports.  It neither opens MT5 nor
updates the operational identity registry.  It records the old/new value and
source hashes in a reviewable JSON report, so a later admission can create the
separate append-only operational identity event.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from assign_unique_magics import MAGIC_PATTERN, read_magic
from magic_identity import IdentityValidationError, load_policy, validate_magic_number


def _load_scope(policy_path: Path, scope_name: str) -> tuple[int, int]:
    raw = json.loads(policy_path.read_text(encoding="utf-8"))
    try:
        scope = raw["allocation_scopes"][scope_name]
        minimum = int(scope["minimum"])
        maximum = int(scope["maximum"])
    except (KeyError, TypeError, ValueError) as error:
        raise IdentityValidationError(f"scope de magic inválido: {scope_name}") from error
    if minimum < 1 or minimum > maximum:
        raise IdentityValidationError(f"rango de scope inválido: {scope_name}")
    return minimum, maximum


def plan_assignment(roots: list[Path], policy_path: Path, scope_name: str) -> list[dict[str, Any]]:
    """Plan a deterministic fresh assignment for all sources under ``roots``."""
    policy = load_policy(policy_path)
    minimum, maximum = _load_scope(policy_path, scope_name)
    sources = sorted({path.resolve() for root in roots for path in root.rglob("*.mq5")})
    if not sources:
        raise IdentityValidationError("no hay fuentes .mq5 en el alcance indicado")
    if len(sources) > maximum - minimum + 1:
        raise IdentityValidationError("el scope no tiene capacidad suficiente")

    rows: list[dict[str, Any]] = []
    for offset, source in enumerate(sources):
        old_magic = read_magic(source)
        if old_magic is None:
            raise IdentityValidationError(f"MagicNumber ausente: {source}")
        new_magic = minimum + offset
        validate_magic_number(new_magic, policy)
        rows.append(
            {
                "mql5_path": str(source),
                "mql5_sha256_before": hashlib.sha256(source.read_bytes()).hexdigest(),
                "magic_number_before": old_magic,
                "magic_number_after": new_magic,
            }
        )
    return rows


def apply_assignment(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        source = Path(str(row["mql5_path"]))
        current = hashlib.sha256(source.read_bytes()).hexdigest()
        if current != row["mql5_sha256_before"]:
            raise IdentityValidationError(f"fuente modificada desde el plan: {source}")
        text = source.read_text(encoding="utf-8", errors="strict")
        updated, count = MAGIC_PATTERN.subn(
            rf"\g<1>{int(row['magic_number_after'])}", text, count=1
        )
        if count != 1:
            raise IdentityValidationError(f"no se pudo cambiar MagicNumber: {source}")
        source.write_text(updated, encoding="utf-8", newline="\n")
        row["mql5_sha256_after"] = hashlib.sha256(source.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", action="append", type=Path, required=True)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--scope", default="analysis_candidate")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    roots = [root.resolve() for root in args.root]
    rows = plan_assignment(roots, args.policy.resolve(), args.scope)
    if args.apply:
        apply_assignment(rows)
    report = {
        "schema_version": "analysis-candidate-magic-assignment-v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "mode": "APPLY" if args.apply else "DRY_RUN",
        "policy_path": str(args.policy.resolve()),
        "policy_version": load_policy(args.policy.resolve()).policy_version,
        "allocation_scope": args.scope,
        "roots": [str(root) for root in roots],
        "rows": rows,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"mode": report["mode"], "assigned": len(rows), "report": str(args.report)}))


if __name__ == "__main__":
    main()
