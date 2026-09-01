import json
from pathlib import Path

import pytest

from stratos_operational_launcher import LAUNCHER_VERSION, load_config, write_queue_snapshot


def write_config(root: Path, **overrides: object) -> Path:
    (root / ".venv" / "Scripts").mkdir(parents=True)
    (root / ".venv" / "Scripts" / "python.exe").write_bytes(b"")
    (root / ".env.operational").write_text("ignored", encoding="utf-8")
    (root / "analysis").mkdir()
    (root / "projects").mkdir()
    (root / "panel").mkdir()
    (root / "docker-compose.yml").write_text("services: {}", encoding="utf-8")
    (root / "docker-compose.operational.yml").write_text("services: {}", encoding="utf-8")
    payload: dict[str, object] = {
        "version": LAUNCHER_VERSION,
        "python_executable": ".venv/Scripts/python.exe",
        "env_file": ".env.operational",
        "compose_project": "stratos_operational",
        "compose_files": ["docker-compose.yml", "docker-compose.operational.yml"],
        "core_health_url": "http://127.0.0.1:8300/health",
        "core_health_startup_timeout_s": 45,
        "analysis_root": "analysis",
        "projects_root": "projects",
        "panel_dir": "panel",
        "expected_terminal": "Darwinex MetaTrader 5",
        "max_backtests_per_run": 2,
    }
    payload.update(overrides)
    target = root / "launcher.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    return target


def test_load_config_resolves_local_paths(tmp_path: Path) -> None:
    target = write_config(tmp_path)

    config = load_config(tmp_path, target)

    assert config.python_executable == tmp_path / ".venv" / "Scripts" / "python.exe"
    assert config.max_backtests_per_run == 2


def test_load_config_rejects_non_operational_env(tmp_path: Path) -> None:
    target = write_config(tmp_path, env_file=".env.g12")

    with pytest.raises(ValueError, match=".env.operational"):
        load_config(tmp_path, target)


def test_queue_snapshot_is_sealed_and_hides_local_source_paths(tmp_path: Path) -> None:
    target = write_config(tmp_path)
    config = load_config(tmp_path, target)
    prefilter = tmp_path / "runtime" / "operational" / "analysis-prefilter.json"
    prefilter.parent.mkdir(parents=True)
    prefilter.write_text("{}", encoding="utf-8")

    snapshot = write_queue_snapshot(
        config,
        prefilter,
        [{
            "strategy_name": "Candidate A",
            "symbol": "AUDCAD",
            "timeframe": "H4",
            "sqx_path": r"C:\private\source.sqx",
        }],
    )

    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    assert payload["entries"] == [{
        "rank": 1,
        "strategy_name": "Candidate A",
        "symbol": "AUDCAD",
        "timeframe": "H4",
        "state": "PENDING_OPERATOR_CONFIRMATION",
    }]
    assert len(payload["snapshot_sha256"]) == 64
