from pathlib import Path

import pytest

import run_operational_sqx_mt5_backtest as runner
from run_operational_sqx_mt5_backtest import assert_safe_terminal, build_command, seal_payload


def _terminal(**overrides: object) -> dict[str, object]:
    return {
        "id": "Darwinex MetaTrader 5",
        "nombre": "Darwinex MetaTrader 5",
        "algotrading": False,
        "es_real": True,
        **overrides,
    }


def test_real_strategy_tester_requires_explicit_acknowledgement() -> None:
    with pytest.raises(ValueError, match="allow-real"):
        assert_safe_terminal(_terminal(), "Darwinex MetaTrader 5", False)


def test_real_strategy_tester_requires_autotrading_off() -> None:
    with pytest.raises(ValueError, match="AutoTrading"):
        assert_safe_terminal(_terminal(algotrading=True), "Darwinex MetaTrader 5", True)


def test_command_never_selects_a_deployment_target() -> None:
    command = build_command(
        panel_dir=Path("C:/panel"),
        sqx_path=Path("C:/analysis/a.sqx"),
        mq5_path=Path("C:/analysis/a.mq5"),
        output_dir=Path("C:/runtime/run"),
        since="2018-01-01",
        until="2026-08-29",
        symbol="EURUSD",
        timeframe="H1",
    )
    assert "--sqx-path" in command
    assert "--mq5-path" in command
    assert "--strict-real-ticks" in command
    assert "despliegue" not in " ".join(command).lower()


def test_command_passes_a_sealed_algowizard_trade_csv() -> None:
    command = build_command(
        panel_dir=Path("C:/panel"),
        sqx_path=Path("C:/analysis/a.sqx"),
        mq5_path=Path("C:/analysis/a.mq5"),
        sqx_trades_csv=Path("C:/evidence/a-trades.csv"),
        output_dir=Path("C:/runtime/run"),
        since="2018-01-01",
        until="2026-08-29",
        symbol="EURUSD",
        timeframe="H1",
    )
    assert Path(command[command.index("--sqx-trades-csv") + 1]) == Path("C:/evidence/a-trades.csv")


def test_manifest_seal_is_deterministic() -> None:
    assert seal_payload({"b": 2, "a": 1}) == seal_payload({"a": 1, "b": 2})


def test_target_terminal_management_requests_a_clean_close_without_force(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    class ClosedTarget:
        def terminal_abierto(self, _terminal: str) -> bool:
            return False

    def fake_run(command: list[str], **_kwargs: object) -> None:
        calls.append(command)

    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    assert runner.close_target_terminal(ClosedTarget(), r"C:\MT5\terminal64.exe")
    assert "CloseMainWindow" in calls[0][4]
    assert "Stop-Process" not in calls[0][4]
