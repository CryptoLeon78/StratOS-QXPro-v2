"""Crea una propuesta G13 revisada a partir de aliases aprobados por el operador.

No modifica el registro ni MT5. El fichero de overrides referencia el hash de
la propuesta exacta revisada para impedir que un alias se aplique a otro lote.
"""

from __future__ import annotations

import argparse
import copy
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from magic_identity import (
    IdentityValidationError,
    build_comment_identity,
    load_policy,
    next_free_magic,
    normalize_short_label,
    sha256_payload,
    verify_payload_hash,
)
from plan_magic_identity_migration import _registry_magics, write_outputs
from validate_magic_identity import validate_proposal


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposal", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--overrides", type=Path)
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--write-template", action="store_true")
    return parser.parse_args()


def write_template(proposal: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"magic-identity-label-overrides-{proposal['payload_sha256'][:12]}.json"
    overrides = [
        {
            "strategy_key": row["strategy_key"],
            "canonical_strategy_name": row["canonical_strategy_name"],
            "resolved_canonical_strategy_name": None,
            "current_short_strategy_label": row["short_strategy_label"],
            "reason": row["reason"],
            "short_strategy_label": None,
            "deployment_variants": (
                [
                    {
                        "account_label": deployment["account_label"],
                        "short_strategy_label": None,
                        "resolved_canonical_strategy_name": None,
                    }
                    for deployment in row["deployments"]
                ]
                if row["status"] == "WITHHELD_LEGACY_LABEL_CONFLICT"
                else None
            ),
        }
        for row in proposal["rows"]
        if row["status"]
        in {
            "REQUIRES_LABEL_APPROVAL",
            "WITHHELD_CANONICAL_NAME_CONFLICT",
            "WITHHELD_LEGACY_LABEL_CONFLICT",
        }
    ]
    payload = {
        "schema_version": 1,
        "source_proposal_payload_sha256": proposal["payload_sha256"],
        "instructions": (
            "Rellena short_strategy_label con una etiqueta única [A-Za-z0-9_.-]+. "
            "Para un conflicto de nombre canónico o de etiqueta histórica, rellena también "
            "resolved_canonical_strategy_name. Si decides identidades diferentes por cuenta, "
            "rellena deployment_variants para todas las cuentas retenidas."
        ),
        "overrides": overrides,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _read_overrides(path: Path, proposal: dict[str, Any]) -> dict[str, dict[str, str | None]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("source_proposal_payload_sha256") != proposal["payload_sha256"]:
        raise IdentityValidationError("overrides no corresponden al hash de propuesta revisado")
    result: dict[str, dict[str, str | None]] = {}
    for entry in raw.get("overrides", []):
        key = entry.get("strategy_key")
        label = entry.get("short_strategy_label")
        canonical_name = entry.get("resolved_canonical_strategy_name")
        variants = entry.get("deployment_variants")
        if label in (None, "") and canonical_name in (None, "") and variants in (None, []):
            continue
        if not isinstance(key, str):
            raise IdentityValidationError("override de label inválido")
        if label not in (None, "") and not isinstance(label, str):
            raise IdentityValidationError("short_strategy_label inválido")
        if canonical_name not in (None, "") and not isinstance(canonical_name, str):
            raise IdentityValidationError("resolved_canonical_strategy_name inválido")
        if variants is not None:
            if not isinstance(variants, list) or not variants:
                raise IdentityValidationError("deployment_variants inválido")
            for variant in variants:
                if not isinstance(variant, dict):
                    raise IdentityValidationError("variante de despliegue inválida")
                if not isinstance(variant.get("account_label"), str) or not isinstance(
                    variant.get("short_strategy_label"), str
                ):
                    raise IdentityValidationError("variante sin cuenta o label")
        if key in result:
            raise IdentityValidationError("strategy_key repetido en overrides")
        result[key] = {
            "short_strategy_label": label if isinstance(label, str) else None,
            "canonical_strategy_name": canonical_name if isinstance(canonical_name, str) else None,
            "deployment_variants": variants,
        }
    return result


def _account_variant_key(technical_key: str, account_label: str) -> str:
    """Deriva una identidad operativa scoped sin ocultar la evidencia técnica padre."""
    return "sk_v1_" + sha256_payload(
        {
            "identity_scope": "ACCOUNT_DEPLOYMENT",
            "technical_strategy_key": technical_key,
            "account_label": account_label,
        }
    )


def _expand_account_variants(
    row: dict[str, Any], variants: list[dict[str, Any]], policy: Any
) -> list[dict[str, Any]]:
    if row["status"] != "WITHHELD_LEGACY_LABEL_CONFLICT":
        raise IdentityValidationError(
            "sólo un conflicto de label histórico admite variantes por cuenta"
        )
    deployments = row["deployments"]
    by_account = {str(deployment["account_label"]): deployment for deployment in deployments}
    supplied = {str(variant["account_label"]) for variant in variants}
    if supplied != set(by_account) or len(supplied) != len(variants):
        raise IdentityValidationError(
            "las variantes deben cubrir exactamente una vez cada cuenta retenida"
        )
    expanded: list[dict[str, Any]] = []
    for variant in variants:
        account_label = str(variant["account_label"])
        label = str(variant["short_strategy_label"])
        if normalize_short_label(label, policy) != label:
            raise IdentityValidationError("el label de variante no cumple la gramática exacta")
        deployment = by_account[account_label]
        identity = copy.deepcopy(row)
        identity["technical_strategy_key"] = row["strategy_key"]
        identity["strategy_key"] = _account_variant_key(row["strategy_key"], account_label)
        identity["canonical_strategy_name"] = str(
            variant.get("resolved_canonical_strategy_name") or deployment["canonical_strategy_name"]
        )
        identity["short_strategy_label"] = label
        identity["legacy_magic_numbers"] = [int(deployment["legacy_magic_number"])]
        identity["accounts"] = [account_label]
        identity["deployments"] = [copy.deepcopy(deployment)]
        identity["status"] = "PROPOSED"
        identity["reason"] = "ACCOUNT_SCOPED_IDENTITY_APPROVED"
        identity["magic_number"] = None
        identity["comment_identity"] = None
        identity["file_identity"] = None
        identity["comment_length"] = None
        identity["remaining_chars"] = None
        expanded.append(identity)
    return expanded


def apply_overrides(
    proposal: dict[str, Any],
    policy_path: Path,
    overrides: dict[str, dict[str, str | None]],
    registry_path: Path | None,
) -> dict[str, Any]:
    policy = load_policy(policy_path)
    result = copy.deepcopy(proposal)
    result["parent_proposal_payload_sha256"] = result["payload_sha256"]
    result.pop("payload_sha256")
    rows = result["rows"]
    known_keys = {str(row["strategy_key"]) for row in rows}
    unknown = set(overrides) - known_keys
    if unknown:
        raise IdentityValidationError("override para strategy_key ausente")
    expanded_rows: list[dict[str, Any]] = []
    for row in rows:
        override = overrides.get(str(row["strategy_key"]))
        if override is None:
            expanded_rows.append(row)
            continue
        variants = override.get("deployment_variants")
        if variants is not None:
            expanded_rows.extend(_expand_account_variants(row, variants, policy))
            continue
        canonical_name = override["canonical_strategy_name"]
        if row["status"] in {
            "WITHHELD_CANONICAL_NAME_CONFLICT",
            "WITHHELD_LEGACY_LABEL_CONFLICT",
        }:
            if canonical_name is None:
                continue
            row["canonical_strategy_name"] = canonical_name
        label = override["short_strategy_label"]
        if label is None:
            continue
        # Reusar la normalización como validador fail-closed: si transforma el
        # valor escrito, no se acepta silenciosamente como si fuera idéntico.
        if normalize_short_label(label, policy) != label:
            raise IdentityValidationError("el alias aprobado no cumple la gramática exacta")
        row["short_strategy_label"] = label
        if row["canonical_strategy_name"] is not None:
            row["status"] = "PROPOSED"
            row["reason"] = None
            row["magic_number"] = None
            row["comment_identity"] = None
            row["file_identity"] = None
            row["comment_length"] = None
            row["remaining_chars"] = None
        expanded_rows.append(row)
    result["rows"] = expanded_rows
    rows = expanded_rows
    labels: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["status"] == "PROPOSED":
            labels[str(row["short_strategy_label"])].append(row)
    for same_label in labels.values():
        if len(same_label) < 2:
            continue
        for row in same_label:
            row["status"] = "REQUIRES_LABEL_APPROVAL"
            row["reason"] = "DUPLICATE_SHORT_STRATEGY_LABEL"
    used = _registry_magics(registry_path)
    for row in sorted(rows, key=lambda item: str(item["strategy_key"])):
        if row["status"] != "PROPOSED":
            continue
        magic = next_free_magic(used, policy)
        try:
            comment = build_comment_identity(str(row["short_strategy_label"]), magic, policy)
        except IdentityValidationError as error:
            row["status"] = "REQUIRES_LABEL_APPROVAL"
            row["reason"] = str(error)
            continue
        row["magic_number"] = magic
        row["comment_identity"] = comment
        row["file_identity"] = comment
        row["comment_length"] = len(comment)
        row["remaining_chars"] = policy.max_chars - len(comment)
        used.add(magic)
    result["created_at_utc"] = datetime.now(UTC).isoformat()
    result["summary"] = {
        "eligible_deployments": result["summary"]["eligible_deployments"],
        "source_withheld_deployments": result["summary"]["source_withheld_deployments"],
        "strategies": len(rows),
    }
    for row in rows:
        result["summary"][str(row["status"])] = result["summary"].get(str(row["status"]), 0) + 1
    result["payload_sha256"] = sha256_payload(result)
    validate_proposal(result, policy_path)
    return result


def main() -> None:
    args = parse_args()
    proposal = json.loads(args.proposal.read_text(encoding="utf-8"))
    verify_payload_hash(proposal)
    if args.write_template:
        path = write_template(proposal, args.output_dir)
        print(json.dumps({"template": str(path)}))
        return
    if args.overrides is None:
        raise SystemExit("BLOQUEADO: usa --write-template o indica --overrides")
    revised = apply_overrides(
        proposal, args.policy, _read_overrides(args.overrides, proposal), args.registry
    )
    json_path, csv_path = write_outputs(revised, args.output_dir)
    print(
        json.dumps(
            {"proposal": str(json_path), "csv": str(csv_path), "summary": revised["summary"]}
        )
    )


if __name__ == "__main__":
    main()
