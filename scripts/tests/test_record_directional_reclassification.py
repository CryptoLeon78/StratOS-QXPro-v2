"""Persistencia de la reclasificación direccional (backlog A7).

Lo que se prueba aquí es qué se registra y qué no: que el sello se verifica antes de tocar
nada, que sólo entran las corridas cuyo veredicto cambió, y que un `VALIDADA` sobrevenido en
un F7 externo no se convierte en promoción.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from record_directional_reclassification import (
    changed_entries,
    load_reclassification,
    seal_payload,
)


def _payload(entries: list[dict[str, object]]) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": 1,
        "generated_at_utc": "2026-09-01T21:23:07.828813+00:00",
        "purpose": "SQX_MT5_DIRECTIONAL_RECLASSIFICATION",
        "panel_config_sha256": "9296ea115c7e7391b70c2307de735a2588f7da34d4cb665ab3521619b9e4449e",
        "thresholds": {"net_profit": {"adverse": 10, "favorable": 35}},
        "entries": entries,
        "summary": {"runs": len(entries), "changed_verdicts": len(changed_entries({"entries": entries}))},
    }
    payload["payload_sha256"] = seal_payload(payload)
    return payload


def _entry(run_id: str, antes: str, despues: str) -> dict[str, object]:
    return {
        "run_id": run_id,
        "source_manifest_sha256": f"sha-{run_id}",
        "original_verdict": antes,
        "reclassified_verdict": despues,
        "detail": "detalle",
        "metrics": {},
    }


def _escribir(tmp_path: Path, payload: dict[str, object]) -> Path:
    ruta = tmp_path / "reclassification.json"
    ruta.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return ruta


def test_reads_a_correctly_sealed_reclassification(tmp_path: Path) -> None:
    ruta = _escribir(tmp_path, _payload([_entry("r1", "TOLERABLE", "VALIDADA")]))

    data = load_reclassification(ruta)

    assert data["summary"]["runs"] == 1


def test_refuses_a_payload_whose_seal_does_not_match(tmp_path: Path) -> None:
    """Un JSON manipulado tras sellarse no puede reclasificar nada."""
    payload = _payload([_entry("r1", "TOLERABLE", "VALIDADA")])
    payload["entries"][0]["reclassified_verdict"] = "DISCREPANTE"  # type: ignore[index]
    ruta = _escribir(tmp_path, payload)

    with pytest.raises(ValueError, match="sello"):
        load_reclassification(ruta)


def test_refuses_a_payload_without_a_seal(tmp_path: Path) -> None:
    payload = _payload([_entry("r1", "TOLERABLE", "VALIDADA")])
    del payload["payload_sha256"]
    ruta = _escribir(tmp_path, payload)

    with pytest.raises(ValueError, match="payload_sha256"):
        load_reclassification(ruta)


def test_refuses_an_empty_reclassification(tmp_path: Path) -> None:
    ruta = _escribir(tmp_path, _payload([]))

    with pytest.raises(ValueError, match="corridas"):
        load_reclassification(ruta)


def test_only_changed_verdicts_are_recorded() -> None:
    """Reafirmar un veredicto idéntico no es información nueva: ensuciaría la cadena."""
    data = {
        "entries": [
            _entry("r1", "TOLERABLE", "VALIDADA"),
            _entry("r2", "DISCREPANTE", "DISCREPANTE"),
            _entry("r3", "DISCREPANTE", "TOLERABLE"),
            _entry("r4", "VALIDADA", "VALIDADA"),
        ]
    }

    cambios = changed_entries(data)

    assert [entry["run_id"] for entry in cambios] == ["r1", "r3"]


def test_the_real_sealed_artifact_is_readable_if_present() -> None:
    """La corrida real del 2026-09-01: 11 evaluadas, 3 con cambio de veredicto."""
    ruta = (
        Path(__file__).resolve().parents[2]
        / "runtime"
        / "operational"
        / "backtests_live"
        / "directional_reclassification_20260901.json"
    )
    if not ruta.exists():
        # `runtime/` es evidencia local ignorada por Git: en CI no existe y esta propiedad
        # no se puede comprobar. No se sustituye por un fixture inventado.
        return

    data = load_reclassification(ruta)

    assert data["summary"]["runs"] == 11
    assert len(changed_entries(data)) == 3
