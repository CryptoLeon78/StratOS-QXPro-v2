import argparse
import json
from pathlib import Path

import pytest

from scripts.install_g12_mt5_indicators import install, required_indicators


def _ea(root: Path, name: str, indicator: str) -> None:
    path = root / "MQL5" / "Experts" / "StratOS_G12" / f"{name}.mq5"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'int x = iCustom(_Symbol, PERIOD_H1, "{indicator}", 1);', encoding="utf-8")


def test_required_indicators_uses_only_ready_eas(tmp_path: Path) -> None:
    terminal = tmp_path / "terminal"
    _ea(terminal, "ready", "SqATR")
    _ea(terminal, "held", "SqIgnore")
    manifest = {"candidates": [{"strategy_name": "ready", "status": "READY"}, {"strategy_name": "held", "status": "WITHHELD"}]}
    assert required_indicators(manifest, terminal) == ["SqATR"]


def test_apply_copies_exact_required_sources(tmp_path: Path) -> None:
    terminal = tmp_path / "terminal"
    _ea(terminal, "ready", "SqATR")
    source_root = tmp_path / "sources"
    source_root.mkdir()
    (source_root / "SqATR.mq5").write_text("indicator", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"candidates": [{"strategy_name": "ready", "status": "READY"}]}), encoding="utf-8")
    report = tmp_path / "runtime" / "indicators.json"
    payload = install(
        argparse.Namespace(
            manifest=manifest,
            terminal_data_root=terminal,
            indicator_source_root=source_root,
            metaeditor_exe=tmp_path / "metaeditor64.exe",
            report=report,
            apply=True,
            resume=False,
            compile=False,
        )
    )
    assert payload["required_count"] == 1
    assert (terminal / "MQL5" / "Indicators" / "SqATR.mq5").read_text(encoding="utf-8") == "indicator"


def test_missing_indicator_source_fails_closed(tmp_path: Path) -> None:
    terminal = tmp_path / "terminal"
    _ea(terminal, "ready", "SqATR")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"candidates": [{"strategy_name": "ready", "status": "READY"}]}), encoding="utf-8")
    with pytest.raises(ValueError, match="no existe fuente"):
        install(
            argparse.Namespace(
                manifest=manifest,
                terminal_data_root=terminal,
                indicator_source_root=tmp_path / "sources",
                report=tmp_path / "report.json",
                apply=False,
                resume=False,
            )
        )
