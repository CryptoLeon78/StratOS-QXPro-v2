"""Prepara pares SQX/MQL5 para comparar backtest tick-real y OOS real."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

from import_external_ea_inventory_records import _version, parse_records


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def live_rows(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.read_text(encoding="utf-8").splitlines(), delimiter=";"))


def magic_for(expert_name: str, records: list[object]) -> int | None:
    exact = [record for record in records if record.strategy_name.casefold() == expert_name.casefold()]
    if len(exact) == 1:
        return exact[0].magic_number
    version = _version(expert_name)
    if version is None:
        simple = re.findall(r"\d+\.\d+", expert_name)
        version = simple[-1] if simple else None
    matches = [record for record in records if version and (version in record.strategy_name or version in record.comment_identity)]
    if len(matches) > 1:
        compact_expert = re.sub(r"[^a-z0-9]", "", expert_name.casefold())
        narrowed = [
            record for record in matches
            if (prefix := re.match(r"[a-z]+\d*", record.comment_identity.casefold()))
            and prefix.group(0) in compact_expert
        ]
        if len(narrowed) == 1:
            return narrowed[0].magic_number
    return matches[0].magic_number if len(matches) == 1 else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--account-label", choices=("BEPB", "JJTI"), required=True)
    parser.add_argument("--account-login", required=True)
    parser.add_argument("--live-csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    records = parse_records(args.records, args.account_label)
    output_rows: list[dict[str, object]] = []
    for live in live_rows(args.live_csv):
        expert = live["expert_name"]
        if expert in {"", "PortfolioLive_Manager", "SQXExpertBotTelegramv12"}:
            continue
        folder = args.source_root / expert
        files = list(folder.glob("*")) if folder.is_dir() else []
        sqx = [path for path in files if path.suffix.lower() == ".sqx"]
        mq5 = [path for path in files if path.suffix.lower() == ".mq5"]
        magic = magic_for(expert, records)
        status = "READY_FOR_TICK_BACKTEST" if magic is not None and len(sqx) == 1 and len(mq5) == 1 else "WITHHELD_SOURCE_INCOMPLETE_OR_AMBIGUOUS"
        output_rows.append({
            "account_login": args.account_login, "expert_name": expert, "magic_number": magic,
            "symbol": live["symbol"], "timeframe": live["timeframe"], "live_chart_id": live["chart_id"],
            "sqx_path": str(sqx[0]) if len(sqx) == 1 else None,
            "mq5_path": str(mq5[0]) if len(mq5) == 1 else None,
            "sqx_sha256": sha256(sqx[0]) if len(sqx) == 1 else None,
            "mq5_sha256": sha256(mq5[0]) if len(mq5) == 1 else None,
            "status": status,
        })
    payload = {"schema_version": 1, "created_at": datetime.now(UTC).isoformat(), "account_login": args.account_login,
               "account_label": args.account_label, "source_root": str(args.source_root), "live_csv_sha256": sha256(args.live_csv),
               "records_sha256": sha256(args.records), "entries": output_rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    ready = sum(row["status"] == "READY_FOR_TICK_BACKTEST" for row in output_rows)
    print(f"entries={len(output_rows)} ready={ready} withheld={len(output_rows)-ready} output={args.output}")


if __name__ == "__main__":
    main()
