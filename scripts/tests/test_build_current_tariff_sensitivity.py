import hashlib
import json
from pathlib import Path

import pytest

from build_current_tariff_sensitivity import build_sensitivity
from record_operational_backtest import load_manifest, seal_payload


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    parent_dir = tmp_path / "parent"
    parent_dir.mkdir()
    report = parent_dir / "report.txt"
    report.write_text("VEREDICTO: VALIDADA\n# Trades 204 2 -2.94%\n", encoding="utf-8")
    deals = parent_dir / "mt5-deals.csv"
    rows = [
        "1;10;AUDCAD;2018.01.01 10:00:00;2018.01.01 10:00:00;0;1.0;buy;in;0.2;-0.38;0;0;;0;0",
        "2;10;AUDCAD;2018.01.02 10:00:00;2018.01.02 10:00:00;0;1.0;sell;out;0.2;-0.38;2.43;0;;0;0",
        "3;11;AUDCAD;2018.02.01 10:00:00;2018.02.01 10:00:00;0;1.0;sell;in;0.2;-0.38;0;0;;0;0",
        "4;11;AUDCAD;2018.02.02 10:00:00;2018.02.02 10:00:00;0;1.0;buy;out;0.2;-0.38;0;0;;0;0",
    ]
    deals.write_text("\n".join(rows), encoding="utf-16")
    reconciliation = parent_dir / "cost-reconciliation.json"
    reconciliation.write_text("{}", encoding="utf-8")
    artifacts = []
    for item in (report, deals, reconciliation):
        artifacts.append(
            {"path": str(item), "sha256": hashlib.sha256(item.read_bytes()).hexdigest()}
        )
    audit = {
        "source": {"sqx_sha256": "a"},
        "cost_comparability": {
            "policy": "REAL_MT5_TICKS_BLOCK_COST_DISCREPANCIES_V1",
            "status": "BLOCKED",
            "comparable": False,
            "transaction_cost_basis": "UNPROVEN",
            "mt5": {
                "spread_model": "REAL_TICKS",
                "spread_evidence": {"verified": True},
                "commission_evidence": {"verified": False},
                "swap_evidence": {"verified": False},
            },
        },
        "empirical_reconciliation": {"path": "cost-reconciliation.json", "status": "BLOCKED"},
    }
    audit["empirical_reconciliation"]["sha256"] = hashlib.sha256(
        reconciliation.read_bytes()
    ).hexdigest()
    audit["audit_sha256"] = seal_payload(audit)
    parent = {
        "run_id": "parent-run",
        "mode": "launch",
        "generated_at_utc": "2026-09-24T08:35:37+02:00",
        "source": {"sqx_sha256": "a", "mq5_sha256": "b"},
        "strategy": {"symbol": "AUDCAD", "timeframe": "H4"},
        "range": {"from": "2017-10-02", "to": "2026-08-21", "real_ticks_required": True},
        "result": {"returncode": 0, "stdout": "VEREDICTO: VALIDADA\n# Trades 204 2 -2.94%"},
        "cost_audit": audit,
        "artifacts": artifacts,
    }
    parent["manifest_sha256"] = seal_payload(parent)
    manifest_path = parent_dir / "run-manifest.json"
    manifest_path.write_text(
        json.dumps(parent, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    tariff = {
        "scenario_as_of": "2026-09-24",
        "instrument": "AUDCAD",
        "source": {
            "url": "https://www.darwinex.com/de/forex-cfds",
            "published_at": "2026-09-21T15:32:00Z",
        },
        "rates": {
            "commission_per_order_per_contract": {"value": 2.5, "currency": "AUD"},
            "swap_long_per_contract_per_day": {"value": 2.6, "currency": "CAD"},
            "swap_short_per_contract_per_day": {"value": -7.9, "currency": "CAD"},
            "swap_rollover": "1 day/s",
        },
    }
    tariff_path = tmp_path / "tariff.json"
    tariff_path.write_text(json.dumps(tariff), encoding="utf-8")
    return manifest_path, tariff_path


def test_builder_derives_sealed_current_tariff_scenario_without_mutating_parent(
    tmp_path: Path,
) -> None:
    manifest_path, tariff_path = _fixture(tmp_path)
    original_bytes = manifest_path.read_bytes()
    tariff = json.loads(tariff_path.read_text(encoding="utf-8"))

    derived_path = build_sensitivity(manifest_path, tmp_path / "out", tariff)

    assert manifest_path.read_bytes() == original_bytes
    manifest, verdict = load_manifest(derived_path)
    sensitivity = manifest["cost_audit"]["cost_comparability"]["current_tariff_sensitivity"]
    assert verdict == "VALIDADA"
    assert sensitivity["tester_application"]["closed_positions"] == 2
    assert (
        sensitivity["tester_application"]["observed_costs"]["commission_total_account_currency"]
        == -1.52
    )
    assert (
        sensitivity["tester_application"]["observed_costs"]["swap_total_account_currency"] == 2.43
    )
    assert sensitivity["tester_application"]["sqx_cost_equivalence_claimed"] is False


def test_builder_rejects_unverified_position_count_or_unsealed_deal_export(tmp_path: Path) -> None:
    manifest_path, tariff_path = _fixture(tmp_path)
    tariff = json.loads(tariff_path.read_text(encoding="utf-8"))
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["artifacts"][1]["sha256"] = "0" * 64
    payload["manifest_sha256"] = seal_payload(
        {key: value for key, value in payload.items() if key != "manifest_sha256"}
    )
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="hash-invalid"):
        build_sensitivity(manifest_path, tmp_path / "out", tariff)
