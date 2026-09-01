import json
from pathlib import Path

import pytest

from run_live_backtest_queue import (
    build_command,
    classify_result,
    f7_identities,
    iter_candidates,
    logged_identities,
    preflight_ready_identities,
)


def test_queue_filters_to_verified_f7_identities(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    queue = tmp_path / "queue.json"
    manifest.write_text(
        json.dumps({"account_login": "1", "records": [
            {"magic_number": 10, "status": "MATCHED_UNIQUE_VERSION"},
            {"magic_number": 11, "status": "WITHHELD"},
        ]}), encoding="utf-8"
    )
    queue.write_text(
        json.dumps({"entries": [
            {"account_login": "1", "magic_number": 10, "status": "READY_FOR_TICK_BACKTEST"},
            {"account_login": "1", "magic_number": 11, "status": "READY_FOR_TICK_BACKTEST"},
            {"account_login": "1", "magic_number": None, "status": "READY_FOR_TICK_BACKTEST"},
        ]}), encoding="utf-8"
    )
    candidates = iter_candidates([queue], f7_identities([manifest]), set())
    assert [item["magic_number"] for item in candidates] == [10]


def test_tick_coverage_failure_is_terminal_but_other_errors_retry() -> None:
    assert classify_result(1, "", "el rango exige ticks reales completos") == "WITHHELD_TICKS"
    assert (
        classify_result(1, "", "no incluye operaciones binarias; use --sqx-trades-csv")
        == "WITHHELD_SOURCE"
    )
    assert classify_result(1, "", "terminal ocupado") == "RETRYABLE_ERROR"
    assert classify_result(0, "ok", "") == "COMPLETED"


def test_legacy_completed_log_is_respected(tmp_path: Path) -> None:
    log = tmp_path / "queue.jsonl"
    log.write_text(
        json.dumps({"account_login": "1", "magic_number": 10, "returncode": 0}) + "\n",
        encoding="utf-8",
    )
    assert logged_identities(log) == {("1", 10)}


def test_preflight_command_cannot_launch_tester(tmp_path: Path) -> None:
    config = {"panel_dir": tmp_path, "expected_terminal": "Darwinex MetaTrader 5"}
    item = {"sqx_path": tmp_path / "strategy.sqx", "mq5_path": tmp_path / "strategy.mq5"}
    command = build_command(config, item, tmp_path, launch=False)
    assert "--launch" not in command
    assert "--manage-backtest-terminal" not in command


def test_queue_passes_the_configured_common_window(tmp_path: Path) -> None:
    config = {
        "panel_dir": tmp_path,
        "expected_terminal": "Darwinex MetaTrader 5",
        "backtest_from": "2018-01-01",
        "backtest_to": "2026-08-28",
    }
    item = {"sqx_path": tmp_path / "strategy.sqx", "mq5_path": tmp_path / "strategy.mq5"}

    command = build_command(config, item, tmp_path, launch=False)

    assert command[-4:] == ["--from", "2018-01-01", "--to", "2026-08-28"]


def test_queue_rejects_a_partial_common_window(tmp_path: Path) -> None:
    config = {
        "panel_dir": tmp_path,
        "expected_terminal": "Darwinex MetaTrader 5",
        "backtest_from": "2018-01-01",
    }
    item = {"sqx_path": tmp_path / "strategy.sqx", "mq5_path": tmp_path / "strategy.mq5"}

    with pytest.raises(ValueError, match="deben configurarse juntos"):
        build_command(config, item, tmp_path, launch=False)


def test_queue_can_require_a_successful_preflight(tmp_path: Path) -> None:
    log = tmp_path / "preflight.jsonl"
    log.write_text(
        "\n".join(
            [
                json.dumps({"account_login": "1", "magic_number": 10, "status": "PREFLIGHT_OK"}),
                json.dumps({"account_login": "1", "magic_number": 11, "status": "WITHHELD_TICKS"}),
            ]
        ) + "\n",
        encoding="utf-8",
    )
    assert preflight_ready_identities(log) == {("1", 10)}
