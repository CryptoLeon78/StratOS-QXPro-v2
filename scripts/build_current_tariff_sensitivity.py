"""Build a sealed current-tariff scenario from a completed REAL_TICKS run.

The parent run is immutable. This derives a separately sealed validation package
from the exact MT5 Tester deal export and a dated broker tariff snapshot; it does
not claim that the historical SQX and MT5 cost models were equivalent.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from record_operational_backtest import VERDICT_PATTERN, seal_payload

MT5_DEAL_COLUMNS = {
    "symbol": 2,
    "deal_type": 7,
    "entry": 8,
    "volume": 9,
    "commission": 10,
    "swap": 11,
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_mt5_deal_observation(path: Path, symbol: str) -> dict[str, Any]:
    """Read the semicolon-delimited UTF-16 MT5 Tester 'List of deals' export."""
    positions = 0
    rows = 0
    commission_total = 0.0
    swap_total = 0.0
    commission_orders = 0
    nonzero_swap_deals = 0
    volumes: set[float] = set()
    directions: set[str] = set()
    with path.open("r", encoding="utf-16", newline="") as handle:
        for row in csv.reader(handle, delimiter=";"):
            if (
                len(row) <= max(MT5_DEAL_COLUMNS.values())
                or row[MT5_DEAL_COLUMNS["symbol"]] != symbol
            ):
                continue
            if row[MT5_DEAL_COLUMNS["entry"]] not in {"in", "out", "in/out", "out by"}:
                continue
            rows += 1
            entry = row[MT5_DEAL_COLUMNS["entry"]]
            if entry in {"out", "out by"}:
                positions += 1
            direction = row[MT5_DEAL_COLUMNS["deal_type"]].casefold()
            if direction in {"buy", "sell"}:
                directions.add(direction)
            volume = float(row[MT5_DEAL_COLUMNS["volume"]])
            if volume > 0:
                volumes.add(volume)
            commission = float(row[MT5_DEAL_COLUMNS["commission"]])
            swap = float(row[MT5_DEAL_COLUMNS["swap"]])
            commission_total += commission
            swap_total += swap
            commission_orders += commission != 0
            nonzero_swap_deals += swap != 0
    if positions <= 0 or rows <= 0:
        raise ValueError(f"MT5 deal export contains no closed deals for {symbol}")
    return {
        "symbol": symbol,
        "closed_positions": positions,
        "deal_rows": rows,
        "commission_orders_with_charge": commission_orders,
        "commission_total_account_currency": round(commission_total, 2),
        "nonzero_swap_deals": nonzero_swap_deals,
        "swap_total_account_currency": round(swap_total, 2),
        "observed_volumes_lots": sorted(volumes),
        "observed_deal_directions": sorted(directions),
        "account_currency": "USD",
        "export_sha256": sha256_file(path),
    }


def _verify_parent(manifest_path: Path) -> tuple[dict[str, Any], str]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    supplied = manifest.pop("manifest_sha256", None)
    if not isinstance(supplied, str) or supplied != seal_payload(manifest):
        raise ValueError("parent manifest seal invalid")
    manifest["manifest_sha256"] = supplied
    if manifest.get("mode") != "launch" or manifest.get("result", {}).get("returncode") != 0:
        raise ValueError("parent run did not complete successfully")
    verdict = VERDICT_PATTERN.search(str(manifest.get("result", {}).get("stdout", "")))
    if verdict is None or verdict.group(1) != "VALIDADA":
        raise ValueError("parent run does not have the VALIDADA verdict")
    if manifest.get("range", {}).get("real_ticks_required") is not True:
        raise ValueError("parent run does not require REAL_TICKS")
    for artifact in manifest.get("artifacts", []):
        source = Path(artifact["path"])
        if not source.is_file() or sha256_file(source) != artifact["sha256"]:
            raise ValueError(f"parent artifact absent or hash-invalid: {source}")
    return manifest, supplied


def build_sensitivity(
    manifest_path: Path,
    output_root: Path,
    tariff_snapshot: dict[str, Any],
) -> Path:
    manifest_path = manifest_path.resolve()
    parent, parent_sha = _verify_parent(manifest_path)
    symbol = str(parent.get("strategy", {}).get("symbol", ""))
    if not symbol or tariff_snapshot.get("instrument") != symbol:
        raise ValueError("tariff snapshot instrument must match the parent strategy")
    source = tariff_snapshot.get("source", {})
    rates = tariff_snapshot.get("rates", {})
    published_at = datetime.fromisoformat(
        str(source.get("published_at", "")).replace("Z", "+00:00")
    )
    parent_time = datetime.fromisoformat(str(parent["generated_at_utc"]).replace("Z", "+00:00"))
    if published_at.tzinfo is None or parent_time.tzinfo is None or published_at > parent_time:
        raise ValueError("tariff snapshot must be published no later than the completed Tester run")
    if "darwinex.com" not in str(source.get("url", "")).casefold():
        raise ValueError("tariff source must be an official Darwinex page")
    commission = rates.get("commission_per_order_per_contract", {})
    swap_long = rates.get("swap_long_per_contract_per_day", {})
    swap_short = rates.get("swap_short_per_contract_per_day", {})

    def valid_rate(value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    if not (
        valid_rate(commission.get("value"))
        and commission["value"] > 0
        and commission.get("currency") == "AUD"
        and valid_rate(swap_long.get("value"))
        and swap_long["value"] != 0
        and swap_long.get("currency") == "CAD"
        and valid_rate(swap_short.get("value"))
        and swap_short["value"] != 0
        and swap_short.get("currency") == "CAD"
        and isinstance(rates.get("swap_rollover"), str)
        and rates["swap_rollover"].strip()
    ):
        raise ValueError("tariff snapshot must declare numeric AUDCAD commission and swap rates")

    deal_entry = next(
        (item for item in parent["artifacts"] if Path(item["path"]).name == "mt5-deals.csv"),
        None,
    )
    if deal_entry is None:
        raise ValueError("parent run does not seal mt5-deals.csv")
    deal_source = Path(deal_entry["path"])
    observation = read_mt5_deal_observation(deal_source, symbol)
    reported = re.search(r"# Trades\s+\d+\s+(\d+)", str(parent["result"].get("stdout", "")))
    if reported is None or int(reported.group(1)) != observation["closed_positions"]:
        raise ValueError("closed position count in deal export differs from the Tester report")

    scenario_as_of = str(tariff_snapshot.get("scenario_as_of", ""))
    datetime.strptime(scenario_as_of, "%Y-%m-%d")
    output_root.mkdir(parents=True, exist_ok=True)
    destination = (
        output_root
        / f"current_tariff_sensitivity_{scenario_as_of.replace('-', '')}_{parent_sha[:12]}"
    )
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite sensitivity package: {destination}")
    destination.mkdir()

    parent_copy = destination / "parent-run-manifest.json"
    shutil.copy2(manifest_path, parent_copy)
    copied_artifacts: list[dict[str, str]] = []
    for artifact in parent["artifacts"]:
        original = Path(artifact["path"])
        copied = destination / original.name
        if copied.exists():
            raise ValueError(f"duplicate artifact name in parent manifest: {original.name}")
        shutil.copy2(original, copied)
        copied_artifacts.append({"path": str(copied), "sha256": artifact["sha256"]})

    source_snapshot_path = destination / "broker-tariff-snapshot.json"
    source_snapshot_path.write_text(
        json.dumps(tariff_snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    snapshot = {
        "schema_version": 1,
        "scenario": "CURRENT_BROKER_TARIFF_SENSITIVITY",
        "scenario_as_of": scenario_as_of,
        "instrument": symbol,
        "source": {
            **source,
            "snapshot_artifact": {
                "path": source_snapshot_path.name,
                "sha256": sha256_file(source_snapshot_path),
            },
        },
        "rates": rates,
        "tester_application": {
            "mode": "MT5_STRATEGY_TESTER",
            "price_model": "REAL_TICKS",
            "range": parent["range"],
            "deal_export": {"path": "mt5-deals.csv", "sha256": observation["export_sha256"]},
            "closed_positions": observation["closed_positions"],
            "exported_closed_positions": observation["closed_positions"],
            "observed_costs": observation,
            "sqx_cost_equivalence_claimed": False,
            "interpretation": (
                "The completed Tester run uses its effective broker tariff schedule for this "
                "scenario; it is not a reconstruction of historical tariff changes and does "
                "not establish SQX fee parity."
            ),
        },
        "parent_manifest_sha256": parent_sha,
    }
    sidecar = destination / "sensitivity-reconciliation.json"
    sidecar.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    copied_artifacts.extend(
        [
            {"path": str(source_snapshot_path), "sha256": sha256_file(source_snapshot_path)},
            {"path": str(sidecar), "sha256": sha256_file(sidecar)},
            {"path": str(parent_copy), "sha256": sha256_file(parent_copy)},
        ]
    )

    derived = dict(parent)
    derived["run_id"] = f"{parent['run_id']}-tariff-{scenario_as_of.replace('-', '')}"
    derived["validation_mode"] = "CURRENT_TARIFF_SENSITIVITY_V1"
    derived["sensitivity_parent_manifest_sha256"] = parent_sha
    derived["artifacts"] = copied_artifacts
    audit = json.loads(json.dumps(parent["cost_audit"]))
    comparison = audit["cost_comparability"]
    comparison.update(
        {
            "policy": "CURRENT_TARIFF_SENSITIVITY_V1",
            "status": "SCENARIO_VALIDATED",
            "comparable": True,
            "transaction_cost_basis": "CURRENT_BROKER_TARIFF_SCENARIO",
            "current_tariff_sensitivity": snapshot,
        }
    )
    audit["empirical_reconciliation"] = {
        "path": sidecar.name,
        "sha256": sha256_file(sidecar),
        "status": "SCENARIO_VALIDATED",
    }
    audit["seal_allowed"] = True
    audit["audit_sha256"] = seal_payload(
        {key: value for key, value in audit.items() if key != "audit_sha256"}
    )
    derived["cost_audit"] = audit
    derived.pop("manifest_sha256", None)
    derived["manifest_sha256"] = seal_payload(derived)
    target_manifest = destination / "run-manifest.json"
    target_manifest.write_text(
        json.dumps(derived, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return target_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--tariff-snapshot", type=Path, required=True)
    args = parser.parse_args()
    tariff_snapshot = json.loads(args.tariff_snapshot.read_text(encoding="utf-8"))
    print(build_sensitivity(args.manifest, args.output_root, tariff_snapshot))


if __name__ == "__main__":
    main()
