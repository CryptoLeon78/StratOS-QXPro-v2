import json
from pathlib import Path

import pytest

from record_operational_backtest import load_manifest, seal_payload


def _write_manifest(tmp_path: Path, *, verdict: str = "DISCREPANTE") -> Path:
    artifact = tmp_path / "report.txt"
    artifact.write_text("report", encoding="utf-8")
    payload = {
        "run_id": "run-1",
        "mode": "launch",
        "source": {"sqx_sha256": "a", "mq5_sha256": "b"},
        "range": {"from": "2018-01-01", "to": "2026-08-30"},
        "result": {"returncode": 0, "stdout": f"VEREDICTO: {verdict}"},
        "artifacts": [{"path": str(artifact), "sha256": __import__("hashlib").sha256(artifact.read_bytes()).hexdigest()}],
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


def test_load_manifest_relocates_a_sealed_artifact_into_its_runtime_directory(tmp_path: Path) -> None:
    manifest_path = _write_manifest(tmp_path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["artifacts"][0]["path"] = r"C:\original-host\report.txt"
    unsigned = {key: value for key, value in payload.items() if key != "manifest_sha256"}
    payload["manifest_sha256"] = seal_payload(unsigned)
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    manifest, _ = load_manifest(manifest_path)

    assert Path(manifest["artifacts"][0]["path"]).parent == tmp_path
