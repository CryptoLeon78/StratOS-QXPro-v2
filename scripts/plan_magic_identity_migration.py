"""Propone identidades G13 desde manifiestos F7 sellados, sin tocar MT5.

Sólo acepta asociaciones EX5 ya contrastadas. Agrupa por evidencia técnica
(hash EX5, símbolo y timeframe), no por nombre, ruta ni cuenta. El resultado
es una propuesta revisable; nunca es una aprobación ni modifica un registro.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from magic_identity import (
    IdentityValidationError,
    build_comment_identity,
    load_policy,
    next_free_magic,
    normalize_short_label,
    parse_comment_identity,
    sha256_payload,
    strategy_key,
)

ELIGIBLE_STATUSES = frozenset({"MATCHED_EQUIVALENT_EX5_COPIES", "MATCHED_UNIQUE_VERSION"})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", action="append", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--registry", type=Path, help="Registro JSONL existente, sólo lectura.")
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def _hash_files(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: str(item.resolve()).casefold()):
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _registry_magics(path: Path | None) -> set[int]:
    if path is None or not path.exists():
        return set()
    used: set[int] = set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
            if event["event_type"] in {
                "ASSIGNED",
                "MIGRATION_PLANNED",
                "MIGRATION_OBSERVED",
                "RETIRED",
            }:
                used.add(int(event["magic_number"]))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise SystemExit(f"registro inválido en línea {number}") from error
    return used


def _load_rows(paths: list[Path], policy: Any) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    withheld = 0
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        login = str(payload["account_login"])
        account_label = str(payload["account_label"])
        for raw in payload["records"]:
            if str(raw.get("status")) not in ELIGIBLE_STATUSES:
                withheld += 1
                continue
            required = (
                "strategy_name",
                "comment_identity",
                "magic_number",
                "symbol",
                "timeframe",
                "ea_sha256",
            )
            if any(raw.get(key) in (None, "") for key in required):
                withheld += 1
                continue
            evidence = {
                "ea_sha256": str(raw["ea_sha256"]),
                "symbol": str(raw["symbol"]),
                "timeframe": str(raw["timeframe"]),
            }
            try:
                legacy_label, parsed_magic = parse_comment_identity(
                    str(raw["comment_identity"]), policy
                )
            except IdentityValidationError:
                withheld += 1
                continue
            if parsed_magic != int(raw["magic_number"]):
                withheld += 1
                continue
            rows.append(
                {
                    "account_login": login,
                    "account_label": account_label,
                    "canonical_strategy_name": str(raw["strategy_name"]),
                    "legacy_magic_number": int(raw["magic_number"]),
                    "legacy_comment_identity": str(raw["comment_identity"]),
                    "legacy_short_strategy_label": legacy_label,
                    "ea_sha256": evidence["ea_sha256"],
                    "symbol": evidence["symbol"],
                    "timeframe": evidence["timeframe"],
                    "strategy_key": strategy_key(evidence, policy),
                }
            )
    return rows, withheld


def build_proposal(
    manifest_paths: list[Path], policy_path: Path, registry_path: Path | None
) -> dict[str, Any]:
    policy = load_policy(policy_path)
    rows, withheld = _load_rows(manifest_paths, policy)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["strategy_key"]].append(row)
    used_magics = _registry_magics(registry_path)
    proposal_rows: list[dict[str, Any]] = []
    for key in sorted(grouped):
        deployments = grouped[key]
        names = {row["canonical_strategy_name"] for row in deployments}
        labels = {row["legacy_short_strategy_label"] for row in deployments}
        legacy_magics = sorted({int(row["legacy_magic_number"]) for row in deployments})
        accounts = sorted({str(row["account_label"]) for row in deployments})
        status = "PROPOSED"
        reason: str | None = None
        label = ""
        comment: str | None = None
        magic: int | None = None
        if len(labels) != 1:
            status, reason = "WITHHELD_LEGACY_LABEL_CONFLICT", "LEGACY_COMMENT_LABEL_CONFLICT"
        elif len(names) != 1:
            status, reason = "WITHHELD_CANONICAL_NAME_CONFLICT", "CANONICAL_NAME_CONFLICT"
        else:
            try:
                label = next(iter(labels))
                if normalize_short_label(label, policy) != label:
                    raise IdentityValidationError("etiqueta del comment legado inválida")
                magic = next_free_magic(used_magics, policy)
                comment = build_comment_identity(label, magic, policy)
                used_magics.add(magic)
            except IdentityValidationError as error:
                status, reason = "REQUIRES_LABEL_APPROVAL", str(error)
                if magic is not None:
                    used_magics.discard(magic)
        proposal_rows.append(
            {
                "strategy_key": key,
                "canonical_strategy_name": next(iter(names)) if len(names) == 1 else None,
                "short_strategy_label": label or None,
                "comment_identity": comment,
                "file_identity": comment,
                "comment_length": len(comment) if comment is not None else None,
                "remaining_chars": policy.max_chars - len(comment) if comment is not None else None,
                "magic_number": magic,
                "legacy_magic_numbers": legacy_magics,
                "accounts": accounts,
                "deployments": sorted(
                    deployments, key=lambda row: (row["account_label"], row["legacy_magic_number"])
                ),
                "status": status,
                "reason": reason,
            }
        )
    label_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in proposal_rows:
        if row["status"] == "PROPOSED":
            label_groups[str(row["short_strategy_label"])].append(row)
    for duplicate_rows in label_groups.values():
        if len(duplicate_rows) < 2:
            continue
        for row in duplicate_rows:
            row["status"] = "REQUIRES_LABEL_APPROVAL"
            row["reason"] = "DUPLICATE_SHORT_STRATEGY_LABEL"
            row["magic_number"] = None
            row["comment_identity"] = None
            row["file_identity"] = None
            row["comment_length"] = None
            row["remaining_chars"] = None
    # Reasigna sólo a propuestas válidas: las filas retenidas no consumen un magic.
    used_magics = _registry_magics(registry_path)
    for row in sorted(proposal_rows, key=lambda item: str(item["strategy_key"])):
        if row["status"] != "PROPOSED":
            continue
        magic = next_free_magic(used_magics, policy)
        comment = build_comment_identity(str(row["short_strategy_label"]), magic, policy)
        row["magic_number"] = magic
        row["comment_identity"] = comment
        row["file_identity"] = comment
        row["comment_length"] = len(comment)
        row["remaining_chars"] = policy.max_chars - len(comment)
        used_magics.add(magic)
    result = {
        "schema_version": 1,
        "proposal_kind": "G13_MAGIC_IDENTITY_DRY_RUN",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "mode": "DRY_RUN",
        "policy_version": policy.policy_version,
        "policy_sha256": hashlib.sha256(policy_path.read_bytes()).hexdigest(),
        "source_manifests_sha256": _hash_files(manifest_paths),
        "summary": {
            "eligible_deployments": len(rows),
            "source_withheld_deployments": withheld,
            "strategies": len(proposal_rows),
            **Counter(str(row["status"]) for row in proposal_rows),
        },
        "rows": proposal_rows,
    }
    result["payload_sha256"] = sha256_payload(result)
    return result


def write_outputs(proposal: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"magic-identity-proposal-{proposal['payload_sha256'][:12]}"
    json_path = output_dir / f"{stem}.json"
    csv_path = output_dir / f"{stem}.csv"
    json_path.write_text(
        json.dumps(proposal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    fields = (
        "strategy_key",
        "technical_strategy_key",
        "canonical_strategy_name",
        "short_strategy_label",
        "magic_number",
        "comment_identity",
        "file_identity",
        "comment_length",
        "remaining_chars",
        "accounts",
        "legacy_magic_numbers",
        "status",
        "reason",
    )
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in proposal["rows"]:
            writer.writerow(
                {
                    **row,
                    "accounts": ";".join(row["accounts"]),
                    "legacy_magic_numbers": ";".join(map(str, row["legacy_magic_numbers"])),
                }
            )
    return json_path, csv_path


def main() -> None:
    args = parse_args()
    proposal = build_proposal(args.manifest, args.policy, args.registry)
    json_path, csv_path = write_outputs(proposal, args.output_dir)
    print(
        json.dumps(
            {"proposal": str(json_path), "csv": str(csv_path), "summary": proposal["summary"]},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
