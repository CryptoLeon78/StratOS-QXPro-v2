import argparse
import json
from pathlib import Path

import pytest

from scripts.attach_g12_demo_eas import attach, build_attachments, chart_text


def _candidate(name: str, magic: int, symbol: str, timeframe: str) -> dict:
    return {
        "strategy_name": name,
        "magic_number": magic,
        "darwinex_symbol": symbol,
        "timeframe": timeframe,
        "status": "READY",
    }


def _materialize_ea(root: Path, name: str, magic: int) -> None:
    experts = root / "MQL5" / "Experts" / "StratOS_G12"
    experts.mkdir(parents=True, exist_ok=True)
    source = experts / f"{name}.mq5"
    source.write_text(
        f'input int MagicNumber = {magic};\n'
        'input string StratosReporterVersion = "g12-reporter-v1.1";\n'
        'input string StratosReporterOutbox = "stratos_g12_' + str(magic) + '.jsonl";\n'
        'void x(){ StratosReporterManagedOnInit(); StratosReporterManagedOnTradeTransaction(); }\n',
        encoding="utf-8",
    )
    compiled = experts / f"{name}.ex5"
    compiled.write_bytes(b"compiled")
    compiled.touch()


def _manifest(tmp_path: Path) -> Path:
    candidates = []
    for index in range(11):
        name = f"ea_{index}"
        magic = 1000 + index
        _materialize_ea(tmp_path / "terminal", name, magic)
        candidates.append(_candidate(name, magic, "EURGBP_darwinex", "H1"))
    candidates.append({"strategy_name": "withheld", "status": "WITHHELD", "reasons": ["gate"]})
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"ea_required_version": "g12-reporter-v1.1", "candidates": candidates}), encoding="utf-8")
    return manifest


def test_build_requires_allow_withheld(tmp_path: Path) -> None:
    manifest = json.loads(_manifest(tmp_path).read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="allow-withheld"):
        build_attachments(manifest, tmp_path / "terminal", {"EURGBP_darwinex": "EURGBP"}, False, "PAPER", "50.00")


def test_apply_creates_isolated_profile_with_all_ready_eas(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    symbol_map = tmp_path / "symbols.json"
    symbol_map.write_text(json.dumps({"EURGBP_darwinex": "EURGBP"}), encoding="utf-8")
    report = tmp_path / "runtime" / "attach.json"
    payload = attach(
        argparse.Namespace(
            manifest=manifest,
            terminal_exe=tmp_path / "terminal64.exe",
            terminal_data_root=tmp_path / "terminal",
            symbol_map=symbol_map,
            report=report,
            profile_name="StratOS_G12_Demo_11Ready",
            allow_withheld=True,
            operational_mode="PAPER",
            sizing_pct="50.00",
            verify_live_terminal=False,
            apply=True,
            resume=False,
            replace_profile=False,
        )
    )
    profile = tmp_path / "terminal" / "MQL5" / "Profiles" / "Charts" / "StratOS_G12_Demo_11Ready"
    assert payload["ready_count"] == 11
    assert sorted(path.name for path in profile.iterdir()) == [f"chart{i:02d}.chr" for i in range(1, 12)] + ["order.wnd"]
    assert "path=Experts\\StratOS_G12\\ea_0.ex5" in (profile / "chart01.chr").read_text(encoding="utf-16")
    assert "StratosReporterEnabled=true" in (profile / "chart01.chr").read_text(encoding="utf-16")
    assert (profile / "order.wnd").read_text(encoding="utf-16").splitlines() == [f"chart{i:02d}.chr" for i in range(1, 12)]
    assert report.is_file()
    assert payload["launch_args"] == ["/profile:StratOS_G12_Demo_11Ready"]


def test_resume_rejects_changed_profile(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    symbol_map = tmp_path / "symbols.json"
    symbol_map.write_text(json.dumps({"EURGBP_darwinex": "EURGBP"}), encoding="utf-8")
    base = dict(
        manifest=manifest,
        terminal_exe=tmp_path / "terminal64.exe",
        terminal_data_root=tmp_path / "terminal",
        symbol_map=symbol_map,
        report=tmp_path / "runtime" / "attach.json",
        profile_name="StratOS_G12_Demo_11Ready",
        allow_withheld=True,
        operational_mode="PAPER",
        sizing_pct="50.00",
        verify_live_terminal=False,
        apply=True,
        resume=False,
        replace_profile=False,
    )
    attach(argparse.Namespace(**base))
    profile = tmp_path / "terminal" / "MQL5" / "Profiles" / "Charts" / "StratOS_G12_Demo_11Ready"
    (profile / "chart01.chr").write_text("changed", encoding="utf-16")
    base["resume"] = True
    with pytest.raises(ValueError, match="perfil existente distinto"):
        attach(argparse.Namespace(**base))


def test_replace_profile_preserves_backup(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    symbol_map = tmp_path / "symbols.json"
    symbol_map.write_text(json.dumps({"EURGBP_darwinex": "EURGBP"}), encoding="utf-8")
    base = dict(
        manifest=manifest, terminal_exe=tmp_path / "terminal64.exe", terminal_data_root=tmp_path / "terminal",
        symbol_map=symbol_map, report=tmp_path / "runtime" / "attach.json", profile_name="StratOS_G12_Demo_11Ready",
        allow_withheld=True, operational_mode="PAPER", sizing_pct="50.00", verify_live_terminal=False,
        apply=True, resume=False, replace_profile=False,
    )
    attach(argparse.Namespace(**base))
    profile = tmp_path / "terminal" / "MQL5" / "Profiles" / "Charts" / "StratOS_G12_Demo_11Ready"
    (profile / "chart01.chr").write_text("old", encoding="utf-16")
    base.update(resume=True, replace_profile=True)
    attach(argparse.Namespace(**base))
    assert (profile.with_name("StratOS_G12_Demo_11Ready.backup") / "chart01.chr").read_text(encoding="utf-16") == "old"


def test_chart_contains_explicit_reporter_contract() -> None:
    # The file-writing tests above exercise the real attachment path. This keeps
    # the chart contract assertion independent of an MT5 installation.
    from scripts.attach_g12_demo_eas import Attachment
    rendered = chart_text(Attachment("chart01.chr", "ea", 5, "x", "EURGBP", "H1", "Experts\\StratOS_G12\\ea.ex5", "stratos_g12_5.jsonl", "PAPER", "50.00"), 1)
    assert "MagicNumber=5" in rendered
    assert "StratosReporterOutbox=stratos_g12_5.jsonl" in rendered
    assert "expertmode=0" in rendered
    assert "StratosReporterOperationalMode=PAPER" in rendered
