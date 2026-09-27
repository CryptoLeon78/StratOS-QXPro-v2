from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import parse_qs, urlsplit
import json

import pytest

import run_operational_sqx_mt5_backtest as runner
from run_operational_sqx_mt5_backtest import assert_safe_terminal, build_command, resolve_test_range, seal_payload


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


def test_read_only_preflight_does_not_need_real_tester_launch_acknowledgement() -> None:
    # The caller passes the launch authorization only for --launch; inspection
    # preflight does not open or control the configured real terminal.
    runner.assert_safe_terminal(_terminal(), "Darwinex MetaTrader 5", allow_real=True)
    with pytest.raises(ValueError, match="allow-real"):
        runner.assert_safe_terminal(_terminal(), "Darwinex MetaTrader 5", allow_real=False)


def test_backtest_range_defaults_to_exact_sqx_setup_dates() -> None:
    assert resolve_test_range({"date_from": "2018.06.27", "date_to": "2026.08.28"}, None, None) == (
        "2018-06-27", "2026-08-28",
    )


def test_backtest_range_requires_explicit_dates_when_sqx_has_none() -> None:
    with pytest.raises(ValueError, match="indique --from y --to"):
        resolve_test_range({}, None, None)


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


def test_resolves_sqx_project_databank_from_candidate_path(tmp_path: Path) -> None:
    sqx_root = tmp_path / "sqx"
    candidate = sqx_root / "user" / "projects" / "Project One" / "databanks" / "Forward" / "candidate.sqx"
    candidate.parent.mkdir(parents=True)
    candidate.touch()
    assert runner.sqx_databank_identity(candidate, sqx_root) == ("Project One", "Forward", "candidate")


def test_native_sqx_export_rejects_embedded_url_credentials(tmp_path: Path) -> None:
    sqx_root = tmp_path / "sqx"
    candidate = sqx_root / "user" / "projects" / "P" / "databanks" / "Forward" / "candidate.sqx"
    candidate.parent.mkdir(parents=True)
    candidate.touch()
    with pytest.raises(ValueError, match="no puede incluir credenciales"):
        runner.export_sqx_trade_list(
            sqx_path=candidate, sqx_root=sqx_root, symbol="EURGBP", timeframe="D1",
            output_path=tmp_path / "trade.csv", api_url="http://user:secret@127.0.0.1:8080",
        )


def test_native_sqx_export_requests_full_trade_list_and_validates_cost_column(tmp_path: Path) -> None:
    sqx_root = tmp_path / "sqx"
    candidate = sqx_root / "user" / "projects" / "P" / "databanks" / "Forward" / "candidate.sqx"
    candidate.parent.mkdir(parents=True)
    candidate.touch()
    received: dict[str, object] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers["Content-Length"])
            values = parse_qs(self.rfile.read(length).decode("utf-8"))
            received["path"] = self.path
            received["form"] = values
            target = Path(values["path"][0])
            target.write_text(
                '"Open time";"Close time";"Profit/Loss";"Size";"Comm/Swap"\n'
                '"2026.01.02 03:00:00";"2026.01.02 04:00:00";"12.50";"0.10";"-0.85"\n',
                encoding="utf-8",
            )
            body = json.dumps({"success": "Tradelist exported."}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        output = tmp_path / "run" / "sqx-trades.csv"
        evidence = runner.export_sqx_trade_list(
            sqx_path=candidate, sqx_root=sqx_root, symbol="EURGBP_darwinex", timeframe="D1",
            output_path=output, api_url=f"http://127.0.0.1:{server.server_port}",
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    assert urlsplit(str(received["path"])).path == "/tradelist/P/Forward/candidate/export"
    form = received["form"]
    assert form["resultKey"] == ["Main: EURGBP_darwinex/D1"]
    assert form["direction"] == ["0"]
    assert form["sampleType"] == ["127"]
    assert evidence["cost_column"] == "Comm/Swap"
    assert evidence["trade_rows"] == 1
    assert len(str(evidence["sha256"])) == 64


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
    monkeypatch.setattr(runner.time, "sleep", lambda _seconds: None)

    assert runner.close_target_terminal(ClosedTarget(), r"C:\MT5\terminal64.exe")
    assert len(calls) == 1
    assert "CloseMainWindow" in calls[0][4]
    assert "Stop-Process" not in calls[0][4]


def test_target_terminal_management_retries_after_a_transient_reappearance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # G13-67: el terminal puede reaparecer (PID nuevo) justo durante la
    # confirmación tras un cierre aparente. La primera vez "se cierra" pero
    # reaparece en la confirmación; la segunda vez se cierra de verdad.
    sequence = iter([False, True, False, False])
    calls: list[list[str]] = []

    class ReappearingTarget:
        def terminal_abierto(self, _terminal: str) -> bool:
            return next(sequence)

    def fake_run(command: list[str], **_kwargs: object) -> None:
        calls.append(command)

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    monkeypatch.setattr(runner.time, "sleep", lambda _seconds: None)

    assert runner.close_target_terminal(ReappearingTarget(), r"C:\MT5\terminal64.exe")
    assert len(calls) == 2


def test_target_terminal_management_gives_up_after_max_attempts_if_it_never_settles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    class AlwaysOpenTarget:
        def terminal_abierto(self, _terminal: str) -> bool:
            return True

    def fake_run(command: list[str], **_kwargs: object) -> None:
        calls.append(command)

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    monkeypatch.setattr(runner.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(runner, "CLOSE_ATTEMPT_TIMEOUT_S", 0)

    assert not runner.close_target_terminal(AlwaysOpenTarget(), r"C:\MT5\terminal64.exe")
    assert len(calls) == runner.CLOSE_MAX_ATTEMPTS
