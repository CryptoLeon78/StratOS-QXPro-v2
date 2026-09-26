import hashlib
import importlib.util
import json
import os
import asyncio
from pathlib import Path

import pytest


def module():
    path = Path(__file__).parents[1] / "import_archived_sqx_mt5_evidence.py"
    spec = importlib.util.spec_from_file_location("archived_import", path)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(value)
    return value


def test_requires_evidence_manifest(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="evidence-manifest"):
        module().build_import_manifest(tmp_path, 42)


def test_rejects_missing_artifact(tmp_path: Path) -> None:
    (tmp_path / "evidence-manifest.json").write_text(
        '{"artifacts":[{"name":"x.csv","sha256":"bad"}]}', encoding="utf-8"
    )
    with pytest.raises(ValueError, match="hash mismatch"):
        module().build_import_manifest(tmp_path, 42)


def test_requires_sealed_validada_txt_and_mql5(tmp_path: Path) -> None:
    csv = tmp_path / "trades.csv"
    txt = tmp_path / "verdict.txt"
    csv.write_text("ticket\n1\n", encoding="utf-8")
    txt.write_text("VEREDICTO: TOLERABLE", encoding="utf-8")
    raw = {
        "sqx_path": str(tmp_path / "missing.sqx"),
        "artifacts": [
            {"path": str(csv), "sha256": hashlib.sha256(csv.read_bytes()).hexdigest()},
            {"path": str(txt), "sha256": hashlib.sha256(txt.read_bytes()).hexdigest()},
        ],
    }
    (tmp_path / "evidence-manifest.json").write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="does not contain"):
        module().build_import_manifest(tmp_path, 42)


@pytest.mark.skipif(
    os.getenv("STRATOS_OPERATIONAL_INTEGRATION") != "1",
    reason="requires the isolated operational PostgreSQL container",
)
def test_operational_import_is_idempotent(tmp_path: Path) -> None:
    """Exercise the exact derived manifest and ledger against operational DB."""
    evidence_dir = Path(os.environ["ARCHIVED_EVIDENCE_DIR"])
    candidate_id = int(os.environ["ARCHIVED_CANDIDATE_ID"])
    imported = module()
    manifest = imported.build_import_manifest(evidence_dir, candidate_id)
    manifest["manifest_sha256"] = imported._seal(manifest)
    output = tmp_path / "derived-manifest.json"
    output.write_text(json.dumps(manifest), encoding="utf-8")
    assert asyncio.run(imported.persist(manifest, output, None)) == "already_recorded"
