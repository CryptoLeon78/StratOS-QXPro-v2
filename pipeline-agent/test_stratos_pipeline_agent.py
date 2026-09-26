"""Pruebas de las guardias locales del agente Contabo, sin abrir MT5/SQX."""

import importlib.util
from pathlib import Path

import pytest


def _agent_module():
    path = Path(__file__).with_name("stratos_pipeline_agent.py")
    spec = importlib.util.spec_from_file_location("stratos_pipeline_agent", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_real_targets_must_be_read_only(tmp_path: Path) -> None:
    config = tmp_path / "agent.yaml"
    config.write_text(
        "targets:\n"
        "  ANALYSIS: {}\n"
        "  SQX_VS_MT5_TESTER: {}\n"
        "  CONTABO_INCUBATOR_DEMO: {}\n"
        "  JJTI:\n"
        "    mode: demo_only\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="read_only"):
        _agent_module().load_config(config)


def test_f1_commands_can_only_target_analysis() -> None:
    config = {
        "targets": {
            "ANALYSIS": {},
            "SQX_VS_MT5_TESTER": {},
            "CONTABO_INCUBATOR_DEMO": {},
        }
    }
    command = {"command_type": "SQX_START", "payload": {"target_group": "JJTI"}}
    with pytest.raises(ValueError, match="not executable"):
        _agent_module().validate_command(command, config)


def test_incubator_identity_only_scans_declared_active_profile(tmp_path: Path) -> None:
    module = _agent_module()
    charts = tmp_path / "MQL5" / "Profiles" / "Charts"
    for profile in ("StratOS_Incubadora", "StratOS_Incubadora_Recovery"):
        directory = charts / profile
        directory.mkdir(parents=True)
        (directory / "chart01.chr").write_text("MagicNumber=243\nMagicNumber=295\n", encoding="utf-16")

    observed = module.assert_existing_incubator_identity(
        {"data_root": str(tmp_path), "active_profile": "StratOS_Incubadora", "preserve_magics": [243, 295]}
    )

    assert sorted(observed) == [243, 295]
    assert all(len(paths) == 1 for paths in observed.values())
