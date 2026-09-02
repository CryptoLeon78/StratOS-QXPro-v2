import json
from pathlib import Path

import pytest

from record_operational_backtest import load_manifest, resolve_external_magic, seal_payload


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
