"""Create a separately named, telemetry-only reporter copy of one SQX EA.

The source EA is never overwritten.  The generated copy only adds the StratOS
JSONL reporter; it has no order APIs and retains every original trading input.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


REPORTER_INCLUDE = '#include <StratOS\\StratosReporterAdapter_v11.mqh>'
MARKER = "// STRATOS_INCUBATOR_REPORTER_V11"
MAGIC_PATTERN = re.compile(r"input\s+int\s+MagicNumber\s*=\s*(\d+)\s*;")
CUSTOM_COMMENT_PATTERN = re.compile(r'(input\s+string\s+CustomComment\s*=\s*")[^"]*("\s*;)')
ON_INIT_PATTERN = re.compile(r"int\s+OnInit\s*\(\s*\)\s*\{")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def instrument_source(
    source: str,
    *,
    expected_magic: int,
    reporter_version: str,
    outbox_filename: str,
    operational_mode: str,
    sizing_pct: float,
    custom_comment: str,
) -> str:
    """Return an auditable reporter copy or reject an ambiguous EA shape."""
    if MARKER in source:
        raise ValueError("source already contains an Incubadora reporter marker")
    if "OnTradeTransaction" in source:
        raise ValueError("EA already defines OnTradeTransaction; manual adapter review is required")
    if operational_mode not in {"REAL", "PAPER"}:
        raise ValueError("operational_mode must be REAL or PAPER")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+\.jsonl", outbox_filename):
        raise ValueError("outbox_filename is invalid")
    if sizing_pct <= 0:
        raise ValueError("sizing_pct must be positive")
    if not custom_comment or len(custom_comment) > 30:
        raise ValueError("custom_comment must contain at most 30 characters")

    magic_match = MAGIC_PATTERN.search(source)
    if not magic_match or int(magic_match.group(1)) != expected_magic:
        raise ValueError("MagicNumber does not match the deployment contract")
    include_matches = list(re.finditer(r"^#include[^\n]+\n", source, re.MULTILINE))
    if not include_matches:
        raise ValueError("EA has no include block")
    on_init = ON_INIT_PATTERN.search(source)
    if not on_init:
        raise ValueError("EA has no int OnInit() callback")
    source, comments_replaced = CUSTOM_COMMENT_PATTERN.subn(
        lambda match: match.group(1) + custom_comment + match.group(2), source, count=1
    )
    if comments_replaced != 1:
        raise ValueError("EA has no replaceable CustomComment input")

    result = source[: include_matches[-1].end()] + REPORTER_INCLUDE + "\n" + source[include_matches[-1].end() :]
    inputs = (
        f"\n{MARKER}\n"
        f'input string StratosReporterVersion = "{reporter_version}";\n'
        "input bool StratosReporterEnabled = true;\n"
        f'input string StratosReporterOutbox = "{outbox_filename}";\n'
        f'input string StratosReporterOperationalMode = "{operational_mode}";\n'
        f"input double StratosReporterSizingPct = {sizing_pct:.8f};\n"
    )
    result, replacements = MAGIC_PATTERN.subn(lambda match: match.group(0) + inputs, result, count=1)
    if replacements != 1:
        raise ValueError("could not insert reporter inputs")
    init_call = (
        "\n   if(StratosReporterEnabled) StratosReporterManagedOnInit("
        "StratosReporterOutbox,MagicNumber,StratosReporterVersion,LimitTimeRange,"
        "SignalTimeRangeFrom,SignalTimeRangeTo,StratosReporterOperationalMode,"
        "StratosReporterSizingPct);\n"
    )
    result, replacements = ON_INIT_PATTERN.subn(lambda match: match.group(0) + init_call, result, count=1)
    if replacements != 1:
        raise ValueError("could not insert reporter OnInit callback")
    return result + (
        "\nvoid OnTradeTransaction(const MqlTradeTransaction &transaction,const MqlTradeRequest &request,"
        "const MqlTradeResult &result)\n{\n"
        "   if(StratosReporterEnabled) StratosReporterManagedOnTradeTransaction("
        "StratosReporterOutbox,MagicNumber,transaction,request,result);\n}\n"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--magic", type=int, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--outbox", required=True)
    parser.add_argument("--mode", choices=("REAL", "PAPER"), required=True)
    parser.add_argument("--sizing-pct", type=float, required=True)
    parser.add_argument("--custom-comment", required=True)
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_bytes = args.source.read_bytes()
    source = source_bytes.decode("utf-8", errors="strict")
    instrumented = instrument_source(
        source,
        expected_magic=args.magic,
        reporter_version=args.version,
        outbox_filename=args.outbox,
        operational_mode=args.mode,
        sizing_pct=args.sizing_pct,
        custom_comment=args.custom_comment,
    )
    report = {
        "ok": True,
        "mode": "apply" if args.apply else "dry_run",
        "source": str(args.source),
        "target": str(args.target),
        "magic": args.magic,
        "outbox": args.outbox,
        "custom_comment": args.custom_comment,
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "instrumented_sha256": sha256_text(instrumented),
        "reporter_is_telemetry_only": True,
    }
    if args.apply:
        args.target.parent.mkdir(parents=True, exist_ok=True)
        if args.target.exists() and args.target.read_text(encoding="utf-8", errors="strict") != instrumented:
            raise ValueError("target exists with different content; refusing overwrite")
        args.target.write_bytes(instrumented.encode("utf-8"))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
