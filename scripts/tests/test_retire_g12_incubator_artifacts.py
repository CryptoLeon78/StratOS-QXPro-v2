from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "retire_g12_incubator_artifacts.ps1"


def test_retirement_script_targets_only_g12_artifacts() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "Experts\\StratOS_G12" in source
    assert "StratOS_G12_Demo_11Ready" in source
    assert "stratos_g12_*" in source
    assert "Experts\\StratOS'" not in source
    assert "Stop-Process -Id $TerminalProcessId" in source
