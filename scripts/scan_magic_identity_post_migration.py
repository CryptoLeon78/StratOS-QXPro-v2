"""Contrasta un escaneo MT5 sólo lectura contra una propuesta G13 aprobada.

El escáner que produce el JSON debe aportar cuenta, gráfico, hash EX5, magic,
comment, símbolo y timeframe. Si falta un dato, el resultado queda retenido;
nunca se deduce éxito por nombre, ruta o una coincidencia parcial.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from magic_identity import (
    IdentityValidationError,
    load_policy,
    parse_comment_identity,
    sha256_payload,
    verify_payload_hash,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposal", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--scan-manifest", type=Path)
    parser.add_argument("--profile-scan-manifest", action="append", type=Path)
    parser.add_argument("--visual-confirmation", type=Path)
    parser.add_argument("--retained-exception-manifest", type=Path)
    parser.add_argument("--identity-only-confirmed", action="store_true")
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def _expected_identities(proposal: dict[str, Any]) -> dict[tuple[str, int], dict[str, Any]]:
    expected: dict[tuple[str, int], dict[str, Any]] = {}
    for row in proposal["rows"]:
        if row["status"] != "PROPOSED":
            continue
        for deployment in row["deployments"]:
            expected[(str(deployment["account_login"]), int(row["magic_number"]))] = {
                "file_identity": row["file_identity"],
                "ea_sha256": deployment["ea_sha256"],
                "timeframe": deployment["timeframe"],
            }
    return expected


def _file_identity(value: str) -> str:
    """Return an EA name without only its optional, real EX5 extension."""
    filename = value.replace("\\", "/").rsplit("/", maxsplit=1)[-1]
    return filename[:-4] if filename.lower().endswith(".ex5") else filename


def _effective_profile_comment(value: str) -> str:
    """Represent the persisted MT5 profile encoding for a configured comment."""
    return value.replace(".", "_")


def _symbol_alias(
    policy_path: Path, account_login: str, source_symbol: str, broker_symbol: str
) -> dict[str, str] | None:
    """Resolve an explicit source-to-broker symbol alias, never a heuristic."""
    try:
        raw = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise IdentityValidationError(
            "no se puede leer la política de aliases de símbolo"
        ) from error
    aliases = raw.get("symbol_aliases", [])
    if not isinstance(aliases, list):
        raise IdentityValidationError("symbol_aliases debe ser una lista")
    for item in aliases:
        if not isinstance(item, dict):
            raise IdentityValidationError("alias de símbolo inválido")
        required = ("alias_id", "source_symbol", "broker_symbol", "account_logins")
        if any(key not in item for key in required) or not isinstance(item["account_logins"], list):
            raise IdentityValidationError("alias de símbolo incompleto")
        if (
            account_login in {str(value) for value in item["account_logins"]}
            and source_symbol == str(item["source_symbol"])
            and broker_symbol == str(item["broker_symbol"])
        ):
            return {
                "alias_id": str(item["alias_id"]),
                "source_symbol": source_symbol,
                "broker_symbol": broker_symbol,
            }
    return None


def _retained_exceptions(
    path: Path | None, proposal: dict[str, Any]
) -> dict[tuple[str, int], dict[str, Any]]:
    if path is None:
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise IdentityValidationError("no se puede leer el manifiesto de excepciones") from error
    verify_payload_hash(payload)
    if (
        payload.get("kind") != "G13_OPERATOR_RETAINED_OUT_OF_PROPOSAL"
        or payload.get("parent_proposal_payload_sha256") != proposal["payload_sha256"]
    ):
        raise IdentityValidationError("excepción sin vínculo a la propuesta aprobada")
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise IdentityValidationError("excepción sin entries")
    result: dict[tuple[str, int], dict[str, Any]] = {}
    for entry in entries:
        if (
            not isinstance(entry, dict)
            or entry.get("status") != "OPERATOR_RETAINED_OUT_OF_PROPOSAL"
        ):
            raise IdentityValidationError("entry de excepción inválida")
        pair = (str(entry.get("account_login")), int(entry.get("magic_number")))
        if pair in result:
            raise IdentityValidationError("excepción duplicada para cuenta y magic")
        result[pair] = {**entry, "manifest_payload_sha256": payload["payload_sha256"]}
    return result


def _matches_retained_exception(chart: dict[str, Any], exception: dict[str, Any]) -> bool:
    accepted_comments = {
        str(exception["configured_comment_identity"]),
        str(exception["effective_comment_identity"]),
    }
    symbol_identity = exception["symbol_identity"]
    return (
        _file_identity(str(chart.get("ea_filename"))) == str(exception["file_identity"])
        and str(chart.get("comment_identity")) in accepted_comments
        and str(chart.get("symbol")) == str(symbol_identity["mt5_broker_symbol"])
        and str(chart.get("timeframe")) == str(exception["timeframe"])
        and str(chart.get("ea_sha256")) == str(exception["ea_sha256"])
    )


def load_scan_manifest(args: argparse.Namespace, proposal: dict[str, Any]) -> dict[str, Any]:
    if args.scan_manifest is not None and args.profile_scan_manifest:
        raise SystemExit("usa scan-manifest o profile-scan-manifest, no ambos")
    if args.scan_manifest is not None:
        return json.loads(args.scan_manifest.read_text(encoding="utf-8"))
    if not args.profile_scan_manifest:
        raise SystemExit("falta scan-manifest o profile-scan-manifest")
    if args.visual_confirmation is not None and not args.identity_only_confirmed:
        raise SystemExit("visual-confirmation exige identity-only-confirmed")
    expected = _expected_identities(proposal)
    retained = _retained_exceptions(args.retained_exception_manifest, proposal)
    charts: list[dict[str, Any]] = []
    for path in args.profile_scan_manifest:
        profile = json.loads(path.read_text(encoding="utf-8"))
        account_login = profile.get("account_login")
        conflicting_paths = {
            str(chart_path)
            for conflict in profile.get("profile_chart_id_conflicts", [])
            for chart_path in conflict.get("chart_relative_paths", [])
        }
        for chart in profile.get("charts", []):
            pair = (
                (str(account_login), int(chart["magic_number"]))
                if chart.get("magic_number")
                else None
            )
            inherited = (
                (expected.get(pair) or retained.get(pair)) if pair is not None else None
            )
            charts.append(
                {
                    "account_login": account_login,
                    "chart_id": chart.get("chart_relative_path"),
                    "ea_filename": (
                        inherited["file_identity"]
                        if args.identity_only_confirmed and inherited is not None
                        else chart.get("ea_filename")
                    ),
                    "ea_sha256": (
                        inherited["ea_sha256"]
                        if args.identity_only_confirmed and inherited is not None
                        else chart.get("ea_sha256")
                    ),
                    "magic_number": chart.get("magic_number"),
                    "comment_identity": chart.get("comment_identity"),
                    "symbol": chart.get("symbol"),
                    "timeframe": (
                        inherited["timeframe"]
                        if args.identity_only_confirmed and inherited is not None
                        else chart.get("period")
                    ),
                    "evidence_provenance": (
                        "REMOTE_PROFILE_WITH_F7_INHERITANCE"
                        if args.identity_only_confirmed and inherited is not None
                        else "REMOTE_PROFILE"
                    ),
                    # A repeated root MT5 chart id is collapsed only when all
                    # identity fields agree.  Any conflicting serialization
                    # remains visible and must fail closed downstream.
                    "profile_chart_id_conflict": str(chart.get("chart_relative_path"))
                    in conflicting_paths,
                }
            )
    if args.visual_confirmation is not None:
        visual = json.loads(args.visual_confirmation.read_text(encoding="utf-8"))
        for chart in visual.get("charts", []):
            pair = (str(chart["account_login"]), int(chart["magic_number"]))
            inherited = expected.get(pair)
            if inherited is None:
                raise IdentityValidationError("confirmación visual fuera de la propuesta aprobada")
            charts.append(
                {
                    **chart,
                    "ea_filename": inherited["file_identity"],
                    "ea_sha256": inherited["ea_sha256"],
                    "timeframe": inherited["timeframe"],
                    "evidence_provenance": "OPERATOR_SCREENSHOT_WITH_F7_INHERITANCE",
                }
            )
    return {
        "schema_version": 1,
        "source": "MT5_PROFILE_READ_ONLY",
        "identity_only_confirmed": args.identity_only_confirmed,
        # Persisted EA profiles can retain periods or encode them as
        # underscores. Preserve both exact representations for this
        # source; no other character substitution is accepted.
        "profile_comment_encoding": "period_to_underscore"
        if args.identity_only_confirmed
        else None,
        "charts": charts,
    }


def compare_scan(
    proposal: dict[str, Any],
    scan: dict[str, Any],
    policy_path: Path,
    retained_exceptions: dict[tuple[str, int], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    policy = load_policy(policy_path)
    verify_payload_hash(proposal)
    charts = scan.get("charts")
    if not isinstance(charts, list):
        raise IdentityValidationError("scan-manifest sin charts")
    profile_comment_encoding = scan.get("profile_comment_encoding")
    if profile_comment_encoding not in (None, "period_to_underscore"):
        raise IdentityValidationError("profile_comment_encoding no soportado")
    expected: dict[tuple[str, int], dict[str, Any]] = {}
    retained_exceptions = retained_exceptions or {}
    for row in proposal["rows"]:
        if row["status"] != "PROPOSED":
            continue
        for deployment in row["deployments"]:
            expected[(str(deployment["account_login"]), int(row["magic_number"]))] = {
                "strategy_key": row["strategy_key"],
                "comment_identity": row["comment_identity"],
                "file_identity": row["file_identity"],
                "ea_sha256": deployment["ea_sha256"],
                "symbol": deployment["symbol"],
                "timeframe": deployment["timeframe"],
            }
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for chart in charts:
        pair_keys = ("account_login", "magic_number")
        if any(chart.get(key) in (None, "") for key in pair_keys):
            rows.append(
                {"status": "MIGRATION_UNVERIFIED", "reason": "INCOMPLETE_SCAN", "chart": chart}
            )
            continue
        account = str(chart["account_login"])
        magic = int(chart["magic_number"])
        pair = (account, magic)
        target = expected.get(pair)
        if target is None:
            exception = retained_exceptions.get(pair)
            if exception is not None and _matches_retained_exception(chart, exception):
                rows.append(
                    {
                        "status": "OPERATOR_RETAINED_OUT_OF_PROPOSAL",
                        "reason": exception["reason"],
                        "chart": chart,
                        "retained_exception_payload_sha256": exception["manifest_payload_sha256"],
                    }
                )
                continue
            rows.append(
                {
                    "status": "UNEXPECTED_IDENTITY",
                    "reason": "NOT_IN_APPROVED_PROPOSAL",
                    "chart": chart,
                }
            )
            continue
        seen.add(pair)
        if chart.get("profile_chart_id_conflict"):
            rows.append(
                {
                    "status": "MIGRATION_UNVERIFIED",
                    "reason": "PROFILE_CHART_ID_CONFLICT",
                    "strategy_key": target["strategy_key"],
                    "chart": chart,
                }
            )
            continue
        required = (
            "chart_id",
            "ea_filename",
            "ea_sha256",
            "comment_identity",
            "symbol",
            "timeframe",
        )
        if any(chart.get(key) in (None, "") for key in required):
            rows.append(
                {
                    "status": "MIGRATION_UNVERIFIED",
                    "reason": "INCOMPLETE_SCAN",
                    "strategy_key": target["strategy_key"],
                    "chart": chart,
                }
            )
            continue
        try:
            _, parsed_magic = parse_comment_identity(str(chart["comment_identity"]), policy)
        except IdentityValidationError as error:
            rows.append({"status": "MIGRATION_UNVERIFIED", "reason": str(error), "chart": chart})
            continue
        source_symbol = str(target["symbol"])
        observed_symbol = str(chart["symbol"])
        symbol_alias = _symbol_alias(policy_path, account, source_symbol, observed_symbol)
        configured_comment = str(target["comment_identity"])
        accepted_comments = (configured_comment,)
        if profile_comment_encoding == "period_to_underscore":
            accepted_comments = tuple(
                dict.fromkeys((configured_comment, _effective_profile_comment(configured_comment)))
            )
        observed_comment = str(chart["comment_identity"])
        effective_comment = observed_comment if observed_comment in accepted_comments else None
        symbol_source_malformed = re.fullmatch(r"[A-Za-z][A-Za-z0-9._-]*", source_symbol) is None
        symbol_matches = (
            observed_symbol == source_symbol or symbol_source_malformed or symbol_alias is not None
        )
        exact = (
            parsed_magic == magic
            and effective_comment is not None
            # The approved identity itself can contain dots (for example a
            # strategy version).  ``Path.stem`` would incorrectly interpret
            # the last such dot as an extension.  Only remove a real EX5
            # suffix, then compare the complete deployed filename.
            and _file_identity(str(chart["ea_filename"])) == target["file_identity"]
            and chart["ea_sha256"] == target["ea_sha256"]
            and symbol_matches
            and chart["timeframe"] == target["timeframe"]
        )
        rows.append(
            {
                "status": "MIGRATION_OBSERVED" if exact else "MIGRATION_UNVERIFIED",
                "reason": None if exact else "IDENTITY_MISMATCH",
                "strategy_key": target["strategy_key"],
                "chart": chart,
                "configured_comment_identity": configured_comment,
                "accepted_comment_identities": list(accepted_comments),
                "effective_comment_identity": effective_comment,
                "evidence_provenance": chart.get("evidence_provenance"),
                "source_symbol_corrected_from_live_chart": symbol_source_malformed,
                "symbol_identity": {
                    "f7_source_symbol": source_symbol,
                    "mt5_broker_symbol": observed_symbol,
                    "alias_id": symbol_alias["alias_id"] if symbol_alias is not None else None,
                },
            }
        )
    for pair, target in expected.items():
        if pair not in seen:
            rows.append(
                {
                    "status": "MIGRATION_UNVERIFIED",
                    "reason": "EXPECTED_DEPLOYMENT_ABSENT",
                    "account_login": pair[0],
                    "magic_number": pair[1],
                    "strategy_key": target["strategy_key"],
                }
            )
    result: dict[str, Any] = {
        "schema_version": 1,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "mode": "READ_ONLY_POST_MIGRATION_SCAN",
        "proposal_payload_sha256": proposal["payload_sha256"],
        "scan_sha256": sha256_payload(scan),
        "rows": rows,
    }
    result["summary"] = {
        status: sum(1 for row in rows if row["status"] == status)
        for status in sorted({str(row["status"]) for row in rows})
    }
    result["payload_sha256"] = sha256_payload(result)
    return result


def main() -> None:
    args = parse_args()
    proposal = json.loads(args.proposal.read_text(encoding="utf-8"))
    scan = load_scan_manifest(args, proposal)
    result = compare_scan(
        proposal,
        scan,
        args.policy,
        _retained_exceptions(args.retained_exception_manifest, proposal),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
