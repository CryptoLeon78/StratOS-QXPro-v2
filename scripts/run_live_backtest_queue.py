"""Run a resumable SQX_vs_MT5 queue only for verified external F7 identities."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_TERMINAL_STATUSES = frozenset({"COMPLETED", "WITHHELD_SOURCE", "WITHHELD_TICKS"})
_TICK_FAILURE_MARKERS = ("ticks reales completos", "no hay alias o ticks reales")
_SOURCE_FAILURE_MARKERS = ("no incluye operaciones binarias", "--sqx-trades-csv")


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--queue", type=Path, action="append", required=True)
    parser.add_argument("--f7-manifest", type=Path, action="append", required=True)
    parser.add_argument("--preflight-log", type=Path)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--max-runs", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def f7_identities(paths: list[Path]) -> set[tuple[str, int]]:
    identities: set[tuple[str, int]] = set()
    eligible = {"MATCHED_EQUIVALENT_EX5_COPIES", "MATCHED_UNIQUE_VERSION"}
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        login = str(payload["account_login"])
        for record in payload["records"]:
            if record["status"] in eligible:
                identities.add((login, int(record["magic_number"])))
    return identities


def logged_identities(path: Path) -> set[tuple[str, int]]:
    if not path.is_file():
        return set()
    terminal: set[tuple[str, int]] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        status = event.get("status") or classify_result(
            int(event.get("returncode", 1)),
            str(event.get("stdout", "")),
            str(event.get("stderr", "")),
        )
        if status in _TERMINAL_STATUSES:
            terminal.add((str(event["account_login"]), int(event["magic_number"])))
    return terminal


def preflight_ready_identities(path: Path | None) -> set[tuple[str, int]] | None:
    if path is None:
        return None
    if not path.is_file():
        raise ValueError(f"preflight inexistente: {path}")
    return {
        (str(event["account_login"]), int(event["magic_number"]))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
        for event in [json.loads(line)]
        if event.get("status") == "PREFLIGHT_OK"
    }


def classify_result(returncode: int, stdout: str, stderr: str) -> str:
    if returncode == 0:
        return "COMPLETED"
    detail = f"{stdout}\n{stderr}".casefold()
    if any(marker in detail for marker in _TICK_FAILURE_MARKERS):
        return "WITHHELD_TICKS"
    if any(marker in detail for marker in _SOURCE_FAILURE_MARKERS):
        return "WITHHELD_SOURCE"
    return "RETRYABLE_ERROR"


def iter_candidates(
    queue_paths: list[Path],
    allowed: set[tuple[str, int]],
    completed: set[tuple[str, int]],
    preflight_ready: set[tuple[str, int]] | None = None,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for path in queue_paths:
        for item in json.loads(path.read_text(encoding="utf-8"))["entries"]:
            magic_number = item.get("magic_number")
            if magic_number is None:
                continue
            identity = (str(item["account_login"]), int(magic_number))
            if (
                item["status"] == "READY_FOR_TICK_BACKTEST"
                and identity in allowed
                and identity not in completed
                and (preflight_ready is None or identity in preflight_ready)
            ):
                candidates.append(item)
    return candidates


def build_command(
    config: dict[str, Any], item: dict[str, Any], output_root: Path, *, launch: bool
) -> list[str]:
    runner = Path(__file__).with_name("run_operational_sqx_mt5_backtest.py")
    command = [
        sys.executable, str(runner), "--panel-dir", str(config["panel_dir"]), "--sqx",
        str(item["sqx_path"]), "--mq5", str(item["mq5_path"]), "--output-root",
        str(output_root), "--expected-terminal", str(config["expected_terminal"]),
        "--allow-real-strategy-tester",
    ]
    range_from = config.get("backtest_from")
    range_to = config.get("backtest_to")
    if (range_from is None) != (range_to is None):
        raise ValueError("backtest_from y backtest_to deben configurarse juntos")
    if range_from is not None:
        command.extend(["--from", str(range_from), "--to", str(range_to)])
    if launch:
        command.extend(["--manage-backtest-terminal", "--launch"])
    return command


def main() -> None:
    args = _args()
    if args.max_runs < 1:
        raise SystemExit("--max-runs debe ser mayor que cero")
    config = json.loads(args.config.read_text(encoding="utf-8"))
    allowed = f7_identities(args.f7_manifest)
    candidates = iter_candidates(
        args.queue,
        allowed,
        logged_identities(args.log),
        preflight_ready_identities(args.preflight_log),
    )
    args.log.parent.mkdir(parents=True, exist_ok=True)
    for item in candidates[: args.max_runs]:
        result = subprocess.run(
            build_command(config, item, args.output_root, launch=not args.dry_run),
            text=True,
            capture_output=True,
            check=False,
        )
        event = {
            "started_at": datetime.now(UTC).isoformat(),
            "account_login": item["account_login"],
            "magic_number": item["magic_number"],
            "expert_name": item["expert_name"],
            "status": (
                "PREFLIGHT_OK"
                if args.dry_run and result.returncode == 0
                else classify_result(result.returncode, result.stdout, result.stderr)
            ),
            "returncode": result.returncode,
            "stdout": result.stdout[-2000:],
            "stderr": result.stderr[-2000:],
        }
        with args.log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    action = "preflighted" if args.dry_run else "launched"
    print(f"candidates={len(candidates)} {action}={min(len(candidates), args.max_runs)}")


if __name__ == "__main__":
    main()
