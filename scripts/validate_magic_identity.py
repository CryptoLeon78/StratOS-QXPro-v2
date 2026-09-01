"""Valida una propuesta o registro G13 sin contactar MT5 ni escribir datos."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from magic_identity import (
    IdentityValidationError,
    build_comment_identity,
    load_policy,
    parse_comment_identity,
    verify_payload_hash,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposal", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    return parser.parse_args()


def validate_proposal(payload: dict[str, Any], policy_path: Path) -> dict[str, int]:
    policy = load_policy(policy_path)
    verify_payload_hash(payload)
    if (
        payload.get("proposal_kind") != "G13_MAGIC_IDENTITY_DRY_RUN"
        or payload.get("mode") != "DRY_RUN"
    ):
        raise IdentityValidationError("artefacto no es una propuesta G13 de sólo lectura")
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise IdentityValidationError("propuesta sin filas")
    by_magic: dict[int, str] = {}
    by_label: dict[str, str] = {}
    account_magic: dict[tuple[str, int], str] = {}
    status_count: defaultdict[str, int] = defaultdict(int)
    for row in rows:
        if not isinstance(row, dict):
            raise IdentityValidationError("fila de propuesta inválida")
        status = str(row.get("status"))
        status_count[status] += 1
        if status != "PROPOSED":
            continue
        key = str(row["strategy_key"])
        label = str(row["short_strategy_label"])
        magic = row["magic_number"]
        comment = str(row["comment_identity"])
        if not isinstance(magic, int):
            raise IdentityValidationError("magic propuesto inválido")
        parsed_label, parsed_magic = parse_comment_identity(comment, policy)
        if (
            parsed_label != label
            or parsed_magic != magic
            or build_comment_identity(label, magic, policy) != comment
        ):
            raise IdentityValidationError("comment y magic propuestos no coinciden")
        if row.get("file_identity") != comment:
            raise IdentityValidationError("nombre de archivo no coincide con comment_identity")
        if (
            len(comment) != row["comment_length"]
            or policy.max_chars - len(comment) != row["remaining_chars"]
        ):
            raise IdentityValidationError("longitudes de comment inconsistentes")
        if magic in by_magic and by_magic[magic] != key:
            raise IdentityValidationError("magic propuesto para dos estrategias")
        if label in by_label and by_label[label] != key:
            raise IdentityValidationError("label propuesto para dos estrategias")
        by_magic[magic] = key
        by_label[label] = key
        deployments = row.get("deployments")
        if not isinstance(deployments, list) or not deployments:
            raise IdentityValidationError("estrategia propuesta sin despliegues")
        for deployment in deployments:
            account = str(deployment["account_login"])
            pair = (account, magic)
            if pair in account_magic and account_magic[pair] != key:
                raise IdentityValidationError("colisión account_login + magic_number")
            account_magic[pair] = key
    return dict(status_count)


def main() -> None:
    args = parse_args()
    payload = json.loads(args.proposal.read_text(encoding="utf-8"))
    summary = validate_proposal(payload, args.policy)
    print(json.dumps({"valid": True, "statuses": summary}, sort_keys=True))


if __name__ == "__main__":
    main()
