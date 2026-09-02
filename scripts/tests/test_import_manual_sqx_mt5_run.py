import json
from pathlib import Path

import pytest

from import_manual_sqx_mt5_run import import_manual_run


def _write_inventory(path: Path, sqx: Path, mq5: Path) -> Path:
    import hashlib

    inventory = {
        "items": [
            {
                "sqx_path": str(sqx),
                "mql5_path": str(mq5),
                "sqx_sha256": hashlib.sha256(sqx.read_bytes()).hexdigest(),
                "mql5_sha256": hashlib.sha256(mq5.read_bytes()).hexdigest(),
                "strategy_name": "AUDCAD Strategy 1.2.3",
                "symbol": "AUDCAD_darwinex",
                "timeframe": "H4",
                "status": "STATIC_VALIDATED",
            }
        ]
    }
    path.write_text(json.dumps(inventory), encoding="utf-8")
    return path


def _write_mt5_report(path: Path) -> Path:
    image = path.with_name("chart.png")
    image.write_bytes(b"chart")
    path.write_text(
        "<html><body>AUDCAD Strategy 1.2.3 AUDCAD H4 (2017.11.24 - 2026.08.21)"
        '<img src="chart.png"></body></html>',
        encoding="utf-8",
    )
    return path


def test_report_only_run_is_sealed_but_cannot_be_recorded_as_a_verdict(tmp_path: Path) -> None:
    sqx = tmp_path / "strategy.sqx"
    mq5 = tmp_path / "strategy.mq5"
    sqx.write_bytes(b"sqx")
    mq5.write_text("mq5", encoding="utf-8")
    report = _write_mt5_report(tmp_path / "report.htm")

    manifest_path, result = import_manual_run(
        inventory_path=_write_inventory(tmp_path / "inventory.json", sqx, mq5),
        sqx_path=sqx,
        mq5_path=mq5,
        mt5_report=report,
        output_root=tmp_path / "runtime",
        terminal_id="Darwinex MetaTrader 5",
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert result == "report_only"
    assert manifest["mode"] == "manual_report_only"
    assert manifest["strategy"]["symbol"] == "AUDCAD_darwinex"
    assert manifest["range"] == {"from": "2017-11-24", "to": "2026-08-21", "real_ticks_required": True}
    assert {entry["name"] for entry in manifest["artifacts"]} == {"report.htm", "chart.png"}


def test_import_is_idempotent_for_the_same_evidence(tmp_path: Path) -> None:
    sqx = tmp_path / "strategy.sqx"
    mq5 = tmp_path / "strategy.mq5"
    sqx.write_bytes(b"sqx")
    mq5.write_text("mq5", encoding="utf-8")
    report = _write_mt5_report(tmp_path / "report.htm")
    arguments = {
        "inventory_path": _write_inventory(tmp_path / "inventory.json", sqx, mq5),
        "sqx_path": sqx,
        "mq5_path": mq5,
        "mt5_report": report,
        "output_root": tmp_path / "runtime",
        "terminal_id": "Darwinex MetaTrader 5",
    }

    first_path, first_result = import_manual_run(**arguments)
    second_path, second_result = import_manual_run(**arguments)

    assert first_result == "report_only"
    assert second_result == "already_imported"
    assert first_path == second_path


def test_comparison_with_a_verdict_is_prepared_for_append_only_registration(tmp_path: Path) -> None:
    sqx = tmp_path / "strategy.sqx"
    mq5 = tmp_path / "strategy.mq5"
    sqx.write_bytes(b"sqx")
    mq5.write_text("mq5", encoding="utf-8")
    report = _write_mt5_report(tmp_path / "report.htm")
    comparison = tmp_path / "comparison.txt"
    comparison.write_text("VEREDICTO: VALIDADA", encoding="utf-8")

    manifest_path, result = import_manual_run(
        inventory_path=_write_inventory(tmp_path / "inventory.json", sqx, mq5),
        sqx_path=sqx,
        mq5_path=mq5,
        mt5_report=report,
        comparison_report=comparison,
        output_root=tmp_path / "runtime",
        terminal_id="Darwinex MetaTrader 5",
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert result == "comparison_ready"
    assert manifest["mode"] == "launch"
    assert manifest["result"]["returncode"] == 0
    assert "VEREDICTO: VALIDADA" in manifest["result"]["stdout"]


def test_import_rejects_an_inventory_identity_mismatch(tmp_path: Path) -> None:
    sqx = tmp_path / "strategy.sqx"
    mq5 = tmp_path / "strategy.mq5"
    sqx.write_bytes(b"sqx")
    mq5.write_text("mq5", encoding="utf-8")
    report = _write_mt5_report(tmp_path / "report.htm")
    inventory = _write_inventory(tmp_path / "inventory.json", sqx, mq5)
    payload = json.loads(inventory.read_text(encoding="utf-8"))
    payload["items"][0]["timeframe"] = "H1"
    inventory.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="timeframe"):
        import_manual_run(
            inventory_path=inventory,
            sqx_path=sqx,
            mq5_path=mq5,
            mt5_report=report,
            output_root=tmp_path / "runtime",
            terminal_id="Darwinex MetaTrader 5",
        )


def test_import_reads_a_utf16_mt5_report(tmp_path: Path) -> None:
    sqx = tmp_path / "strategy.sqx"
    mq5 = tmp_path / "strategy.mq5"
    sqx.write_bytes(b"sqx")
    mq5.write_text("mq5", encoding="utf-8")
    report = tmp_path / "report.htm"
    report.write_text(
        "AUDCAD Strategy 1.2.3 AUDCAD H4 (2017.11.24 - 2026.08.21)",
        encoding="utf-16",
    )

    manifest_path, result = import_manual_run(
        inventory_path=_write_inventory(tmp_path / "inventory.json", sqx, mq5),
        sqx_path=sqx,
        mq5_path=mq5,
        mt5_report=report,
        output_root=tmp_path / "runtime",
        terminal_id="Darwinex MetaTrader 5",
    )

    assert manifest_path.is_file()
    assert result == "report_only"
