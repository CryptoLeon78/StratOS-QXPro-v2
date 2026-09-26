import json
import hashlib
from pathlib import Path

import pytest

from record_operational_backtest import load_manifest, resolve_external_magic, seal_payload


def _write_manifest(tmp_path: Path, *, verdict: str = "DISCREPANTE") -> Path:
    artifact = tmp_path / "report.txt"
    artifact.write_text("report", encoding="utf-8")
    reconciliation = tmp_path / "cost-reconciliation.json"
    reconciliation.write_text("{}", encoding="utf-8")
    cost_audit = {
        "source": {"sqx_sha256": "a"},
        "cost_comparability": {
            "policy": "REAL_MT5_TICKS_BLOCK_COST_DISCREPANCIES_V1",
            "status": "PROVEN",
            "comparable": True,
            "mt5": {
                "spread_model": "REAL_TICKS",
                "spread_evidence": {"verified": True},
                "commission_evidence": {"verified": True},
                "swap_evidence": {"verified": True},
            },
        },
    }
    cost_audit["audit_sha256"] = seal_payload(cost_audit)
    cost_audit["empirical_reconciliation"] = {
        "path": reconciliation.name,
        "sha256": __import__("hashlib").sha256(reconciliation.read_bytes()).hexdigest(),
        "status": "PROVEN",
    }
    cost_audit["audit_sha256"] = seal_payload({key: value for key, value in cost_audit.items() if key != "audit_sha256"})
    payload = {
        "run_id": "run-1",
        "mode": "launch",
        "generated_at_utc": "2026-09-24T08:35:37.757882+02:00",
        "source": {"sqx_sha256": "a", "mq5_sha256": "b"},
        "strategy": {"symbol": "AUDCAD", "timeframe": "H4"},
        "cost_audit": cost_audit,
        "range": {"from": "2018-01-01", "to": "2026-08-30"},
        "result": {"returncode": 0, "stdout": f"VEREDICTO: {verdict}"},
        "artifacts": [
            {"path": str(artifact), "sha256": __import__("hashlib").sha256(artifact.read_bytes()).hexdigest()},
            {"path": str(reconciliation), "sha256": __import__("hashlib").sha256(reconciliation.read_bytes()).hexdigest()},
        ],
    }
    payload["manifest_sha256"] = seal_payload(payload)
    manifest = tmp_path / "run-manifest.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    return manifest


def test_load_manifest_verifies_seal_hashes_and_verdict(tmp_path: Path) -> None:
    manifest, verdict = load_manifest(_write_manifest(tmp_path))

    assert verdict == "DISCREPANTE"
    assert manifest["run_id"] == "run-1"


def test_load_manifest_rejects_tampered_evidence(tmp_path: Path) -> None:
    manifest_path = _write_manifest(tmp_path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["result"]["stdout"] = "VEREDICTO: VALIDADA"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="sello"):
        load_manifest(manifest_path)


def test_load_manifest_blocks_backtest_validation_without_proven_costs(tmp_path: Path) -> None:
    manifest_path = _write_manifest(tmp_path, verdict="VALIDADA")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["cost_audit"]["cost_comparability"]["status"] = "BLOCKED"
    payload["cost_audit"]["cost_comparability"]["comparable"] = False
    unsigned_cost_audit = {key: value for key, value in payload["cost_audit"].items() if key != "audit_sha256"}
    payload["cost_audit"]["audit_sha256"] = seal_payload(unsigned_cost_audit)
    unsigned = {key: value for key, value in payload.items() if key != "manifest_sha256"}
    payload["manifest_sha256"] = seal_payload(unsigned)
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="comparabilidad de costes no probada"):
        load_manifest(manifest_path)


def test_verified_complete_combined_transaction_cost_can_replace_separate_components(tmp_path: Path) -> None:
    manifest_path = _write_manifest(tmp_path, verdict="VALIDADA")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    cost = payload["cost_audit"]["cost_comparability"]
    cost["mt5"].pop("commission_evidence")
    cost["mt5"].pop("swap_evidence")
    cost["transaction_cost_basis"] = "SQX_COMBINED_COMM_SWAP_TOTAL"
    cost["mt5"]["transaction_cost_evidence"] = {
        "verified": True,
        "aggregate_match": True,
        "source_column": "Comm/Swap",
        "components_separated_by_sqx": False,
        "full_trade_set_paired": True,
        "matched_trades": 10,
        "sqx_trades": 10,
        "mt5_trades": 10,
        "matched_volume_equal": True,
        "matched_direction_equal": True,
        "trades_with_discrepancy": 0,
        "maximum_absolute_trade_delta": 0.01,
    }
    unsigned_cost_audit = {key: value for key, value in payload["cost_audit"].items() if key != "audit_sha256"}
    payload["cost_audit"]["audit_sha256"] = seal_payload(unsigned_cost_audit)
    unsigned = {key: value for key, value in payload.items() if key != "manifest_sha256"}
    payload["manifest_sha256"] = seal_payload(unsigned)
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    manifest, verdict = load_manifest(manifest_path)
    assert verdict == "VALIDADA"
    assert manifest["cost_audit"]["cost_comparability"]["transaction_cost_basis"] == "SQX_COMBINED_COMM_SWAP_TOTAL"


def test_combined_transaction_cost_cannot_seal_with_unpaired_or_mismatched_evidence(tmp_path: Path) -> None:
    manifest_path = _write_manifest(tmp_path, verdict="VALIDADA")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    cost = payload["cost_audit"]["cost_comparability"]
    cost["transaction_cost_basis"] = "SQX_COMBINED_COMM_SWAP_TOTAL"
    cost["mt5"]["commission_evidence"] = {"verified": False}
    cost["mt5"]["swap_evidence"] = {"verified": False}
    cost["mt5"]["transaction_cost_evidence"] = {
        "verified": True,
        "aggregate_match": True,
        "source_column": "Comm/Swap",
        "components_separated_by_sqx": False,
        "full_trade_set_paired": False,
        "matched_trades": 8,
        "sqx_trades": 10,
        "mt5_trades": 10,
        "matched_volume_equal": True,
        "matched_direction_equal": True,
        "trades_with_discrepancy": 0,
        "maximum_absolute_trade_delta": 0.0,
    }
    unsigned_cost_audit = {key: value for key, value in payload["cost_audit"].items() if key != "audit_sha256"}
    payload["cost_audit"]["audit_sha256"] = seal_payload(unsigned_cost_audit)
    unsigned = {key: value for key, value in payload.items() if key != "manifest_sha256"}
    payload["manifest_sha256"] = seal_payload(unsigned)
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="comparabilidad de costes no probada"):
        load_manifest(manifest_path)


def _write_current_tariff_sensitivity(tmp_path: Path) -> Path:
    manifest_path = _write_manifest(tmp_path, verdict="VALIDADA")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    deals = tmp_path / "mt5-deals.csv"
    deals.write_text("sealed MT5 tester deals", encoding="utf-8")
    deals_sha = hashlib.sha256(deals.read_bytes()).hexdigest()
    parent_sha = payload["manifest_sha256"]
    parent_manifest = tmp_path / "parent-run-manifest.json"
    parent_manifest.write_bytes(manifest_path.read_bytes())
    parent_artifact_sha = hashlib.sha256(parent_manifest.read_bytes()).hexdigest()
    source_snapshot = tmp_path / "broker-tariff-snapshot.json"
    tariff = {
        "schema_version": 1,
        "scenario": "CURRENT_BROKER_TARIFF_SENSITIVITY",
        "scenario_as_of": "2026-09-24",
        "instrument": "AUDCAD",
        "source": {
            "url": "https://www.darwinex.com/de/forex-cfds",
            "published_at": "2026-09-21T15:32:00Z",
            "snapshot_artifact": {"path": source_snapshot.name},
        },
        "rates": {
            "commission_per_order_per_contract": {"value": 2.5, "currency": "AUD"},
            "swap_long_per_contract_per_day": {"value": 2.6, "currency": "CAD"},
            "triple_rollover_weekday": "WEDNESDAY",
        },
        "tester_application": {
            "mode": "MT5_STRATEGY_TESTER",
            "price_model": "REAL_TICKS",
            "range": payload["range"],
            "deal_export": {"path": "mt5-deals.csv", "sha256": deals_sha},
            "closed_positions": 198,
            "exported_closed_positions": 198,
            "sqx_cost_equivalence_claimed": False,
        },
        "parent_manifest_sha256": parent_sha,
    }
    source_snapshot.write_text(
        json.dumps(
            {
            "scenario_as_of": tariff["scenario_as_of"],
            "instrument": tariff["instrument"],
            "source": {
                "url": tariff["source"]["url"],
                "published_at": tariff["source"]["published_at"],
            },
            "rates": tariff["rates"],
            }
        ),
        encoding="utf-8",
    )
    tariff["source"]["snapshot_artifact"]["sha256"] = hashlib.sha256(
        source_snapshot.read_bytes()
    ).hexdigest()
    sensitivity_path = tmp_path / "sensitivity-reconciliation.json"
    sensitivity_path.write_text(json.dumps(tariff), encoding="utf-8")
    sensitivity_sha = hashlib.sha256(sensitivity_path.read_bytes()).hexdigest()
    payload["sensitivity_parent_manifest_sha256"] = parent_sha
    payload["artifacts"].append({"path": str(deals), "sha256": deals_sha})
    payload["artifacts"].append({"path": str(sensitivity_path), "sha256": sensitivity_sha})
    payload["artifacts"].append({"path": str(parent_manifest), "sha256": parent_artifact_sha})
    payload["artifacts"].append(
        {
            "path": str(source_snapshot),
            "sha256": tariff["source"]["snapshot_artifact"]["sha256"],
        }
    )
    cost_audit = payload["cost_audit"]
    comparability = cost_audit["cost_comparability"]
    comparability.update({
        "policy": "CURRENT_TARIFF_SENSITIVITY_V1",
        "status": "SCENARIO_VALIDATED",
        "comparable": True,
        "transaction_cost_basis": "CURRENT_BROKER_TARIFF_SCENARIO",
        "current_tariff_sensitivity": tariff,
    })
    cost_audit["empirical_reconciliation"] = {
        "path": sensitivity_path.name,
        "sha256": sensitivity_sha,
        "status": "SCENARIO_VALIDATED",
    }
    cost_audit["audit_sha256"] = seal_payload(
        {key: value for key, value in cost_audit.items() if key != "audit_sha256"}
    )
    unsigned = {key: value for key, value in payload.items() if key != "manifest_sha256"}
    payload["manifest_sha256"] = seal_payload(unsigned)
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    return manifest_path


def test_current_tariff_sensitivity_can_validate_with_explicit_scope_and_sealed_inputs(
    tmp_path: Path,
) -> None:
    manifest_path = _write_current_tariff_sensitivity(tmp_path)

    manifest, verdict = load_manifest(manifest_path)

    assert verdict == "VALIDADA"
    assert manifest["cost_audit"]["cost_comparability"]["status"] == "SCENARIO_VALIDATED"
    sensitivity = manifest["cost_audit"]["cost_comparability"]["current_tariff_sensitivity"]
    assert sensitivity["tester_application"]["sqx_cost_equivalence_claimed"] is False


def test_current_tariff_sensitivity_rejects_unsealed_or_mismatched_mt5_cost_export(
    tmp_path: Path,
) -> None:
    manifest_path = _write_current_tariff_sensitivity(tmp_path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    tariff = payload["cost_audit"]["cost_comparability"]["current_tariff_sensitivity"]
    tariff["tester_application"]["deal_export"]["sha256"] = "0" * 64
    payload["cost_audit"]["audit_sha256"] = seal_payload(
        {key: value for key, value in payload["cost_audit"].items() if key != "audit_sha256"}
    )
    unsigned = {key: value for key, value in payload.items() if key != "manifest_sha256"}
    payload["manifest_sha256"] = seal_payload(unsigned)
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="comparabilidad de costes no probada"):
        load_manifest(manifest_path)


def test_load_manifest_relocates_a_sealed_artifact_into_its_runtime_directory(tmp_path: Path) -> None:
    manifest_path = _write_manifest(tmp_path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["artifacts"][0]["path"] = r"C:\original-host\report.txt"
    unsigned = {key: value for key, value in payload.items() if key != "manifest_sha256"}
    payload["manifest_sha256"] = seal_payload(unsigned)
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    manifest, _ = load_manifest(manifest_path)

    assert Path(manifest["artifacts"][0]["path"]).parent == tmp_path


def test_reconciliation_artifact_is_found_from_a_windows_source_path(tmp_path: Path) -> None:
    manifest_path = _write_manifest(tmp_path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    reconciliation_artifact = payload["artifacts"][1]
    reconciliation_artifact["path"] = r"C:\original-host\cost-reconciliation.json"
    unsigned = {key: value for key, value in payload.items() if key != "manifest_sha256"}
    payload["manifest_sha256"] = seal_payload(unsigned)
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    manifest, _ = load_manifest(manifest_path)

    assert Path(manifest["artifacts"][1]["path"]).parent == tmp_path


# --- Magic legacy de la cola contra magic vigente de la base (backlog A25) ---------------
#
# La cola y los manifiestos F7 declaran los magics ANTERIORES a la migración MN; la tabla
# `bot` tiene los vigentes desde `sync_bot_magics_to_migration.py`. Registrar una corrida
# pasando el magic de la cola fallaba con "F7 externo no encontrado por cuenta y magic
# exactos" aunque el bot existiera.

def _registry(tmp_path: Path, legacy: int, vigente: int, accounts: list[str]) -> Path:
    ruta = tmp_path / "registry.jsonl"
    ruta.write_text(
        json.dumps(
            {
                "event_type": "ASSIGNED",
                "comment_identity": f"X_MN{vigente}",
                "magic_number": vigente,
                "legacy_magic_numbers": [legacy],
                "accounts": accounts,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return ruta


def test_a_current_magic_resolves_to_itself(tmp_path: Path) -> None:
    """Sin traducción no cambia nada: el magic vigente se busca tal cual."""
    resuelto, via_legacy = resolve_external_magic(13, _registry(tmp_path, 200730, 13, ["JJTI"]))

    assert (resuelto, via_legacy) == (13, False)


def test_a_legacy_magic_from_the_queue_resolves_to_the_current_one(tmp_path: Path) -> None:
    """El caso real: la cola declara 200730 y el bot ya tiene el 13."""
    resuelto, via_legacy = resolve_external_magic(200730, _registry(tmp_path, 200730, 13, ["JJTI"]))

    assert (resuelto, via_legacy) == (13, True)


def test_without_a_registry_the_magic_is_used_as_given(tmp_path: Path) -> None:
    """Sin registro no se inventa una traducción: comportamiento anterior intacto."""
    assert resolve_external_magic(200730, None) == (200730, False)


def test_an_unknown_magic_is_left_untouched(tmp_path: Path) -> None:
    """Un magic que el registro no conoce se pasa tal cual y falla más adelante con su
    mensaje propio, en vez de resolverse a otra cosa."""
    assert resolve_external_magic(999999, _registry(tmp_path, 200730, 13, ["JJTI"])) == (
        999999,
        False,
    )
