"""Prepara copias instrumentadas de EAs G12; no adjunta gráficos ni cambia AutoTrading."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any


INCLUDE = '#include <StratOS\\StratosReporterAdapter_v11.mqh>'
MARKER = "// STRATOS_G12_REPORTER_V11"
MAGIC_LINE = re.compile(r"(input\s+int\s+MagicNumber\s*=\s*\d+\s*;[^\n]*\n)")
ON_INIT = re.compile(r"(int\s+OnInit\s*\(\s*\)\s*\{)")
REQUIRED_REPORTER_SYMBOLS = (
    "StratosJsonEscape",
    "StratosAppendReporterEvent",
    "StratosReportEaState",
    "StratosReportFill",
    "StratosReportRejectedOrder",
)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def reporter_header_is_compatible(contents: str) -> bool:
    """Acepta una revisión ya instalada sólo si expone la API v1.1 read-only."""
    prohibited = ("OrderSend(", "PositionOpen(", "PositionClose(", "CTrade")
    code_without_line_comments = re.sub(r"//.*$", "", contents, flags=re.MULTILINE)
    return all(symbol in code_without_line_comments for symbol in REQUIRED_REPORTER_SYMBOLS) and not any(
        token in code_without_line_comments for token in prohibited
    )


def instrument_source(source: str, version: str, magic_number: int) -> str:
    if MARKER in source:
        raise ValueError("EA ya instrumentado por G12")
    if "OnTradeTransaction" in source:
        raise ValueError("EA ya define OnTradeTransaction; requiere adaptación manual")
    includes = list(re.finditer(r"^#include[^\n]+\n", source, re.MULTILINE))
    if not includes:
        raise ValueError("no se encontró bloque de includes")
    source = source[: includes[-1].end()] + INCLUDE + "\n" + source[includes[-1].end() :]
    reporter_inputs = (
        f"{MARKER}\n"
        f'input string StratosReporterVersion = "{version}";\n'
        'input bool StratosReporterEnabled = true;\n'
        f'input string StratosReporterOutbox = "stratos_g12_{magic_number}.jsonl";\n'
        'input string StratosReporterOperationalMode = "PAPER";\n'
        'input double StratosReporterSizingPct = 50.0;\n'
    )
    source, magic_replacements = MAGIC_LINE.subn(r"\1" + reporter_inputs, source, count=1)
    if magic_replacements != 1:
        raise ValueError("no se encontró input MagicNumber")
    init_call = (
        "\n   if(StratosReporterEnabled) StratosReporterManagedOnInit(StratosReporterOutbox,MagicNumber,"
        "StratosReporterVersion,LimitTimeRange,SignalTimeRangeFrom,SignalTimeRangeTo,"
        "StratosReporterOperationalMode,StratosReporterSizingPct);\n"
    )
    source, init_replacements = ON_INIT.subn(r"\1" + init_call, source, count=1)
    if init_replacements != 1:
        raise ValueError("no se encontró int OnInit()")
    source += (
        "\nvoid OnTradeTransaction(const MqlTradeTransaction &transaction,const MqlTradeRequest &request,"
        "const MqlTradeResult &result)\n{\n"
        "   if(StratosReporterEnabled) StratosReporterManagedOnTradeTransaction(StratosReporterOutbox,MagicNumber,"
        "transaction,request,result);\n}\n"
    )
    return source


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--terminal-data-root", required=True, type=Path)
    parser.add_argument("--reporter-source-root", type=Path, default=Path("mt5-connector/mql5"))
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--resume", action="store_true", help="sólo completa una preparación G12 idéntica")
    parser.add_argument(
        "--refresh-reporter",
        action="store_true",
        help="actualiza únicamente copias G12 ya marcadas tras una corrección del reporter",
    )
    return parser.parse_args()


def prepare(args: argparse.Namespace) -> dict[str, Any]:
    if args.refresh_reporter and (not args.apply or not args.resume):
        raise ValueError("--refresh-reporter exige --apply y --resume")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    ready = [item for item in manifest["candidates"] if item["status"] == "READY"]
    experts_target = args.terminal_data_root / "MQL5" / "Experts" / "StratOS_G12"
    include_target = args.terminal_data_root / "MQL5" / "Include" / "StratOS"
    if experts_target.exists() and not args.resume:
        raise ValueError(f"destino ya existe: {experts_target}; se conserva y no se sobrescribe")
    report: dict[str, Any] = {"ready_count": len(ready), "prepared": [], "refreshed": [], "withheld": []}
    for item in manifest["candidates"]:
        if item["status"] != "READY":
            report["withheld"].append({"strategy_name": item["strategy_name"], "reasons": item["reasons"]})
    for item in ready:
        source_path = Path(item["mq5_path"])
        source = source_path.read_text(encoding="utf-8", errors="ignore")
        instrumented = instrument_source(
            source, str(manifest["ea_required_version"]), int(item["magic_number"])
        )
        report["prepared"].append(
            {
                "strategy_name": item["strategy_name"],
                "magic_number": item["magic_number"],
                "source_sha256": sha256_text(source),
                "instrumented_sha256": sha256_text(instrumented),
                "target": str(experts_target / source_path.name),
            }
        )
        target_path = experts_target / source_path.name
        if args.apply and target_path.exists():
            existing = target_path.read_text(encoding="utf-8", errors="ignore")
            if existing != instrumented:
                if not args.refresh_reporter or MARKER not in existing:
                    raise ValueError(f"EA existente distinto: {target_path}; restaurar o revisar antes de seguir")
                target_path.write_text(instrumented, encoding="utf-8")
                report["refreshed"].append(str(target_path))
        elif args.apply:
            experts_target.mkdir(parents=True, exist_ok=True)
            target_path.write_text(instrumented, encoding="utf-8")
    if args.apply:
        include_target.mkdir(parents=True, exist_ok=True)
        for header in ("StratosReporter_v11.mqh", "StratosReporterAdapter_v11.mqh"):
            source_header = args.reporter_source_root / header
            target_header = include_target / header
            if target_header.exists() and header == "StratosReporter_v11.mqh" and not reporter_header_is_compatible(
                target_header.read_text(encoding="utf-8", errors="ignore")
            ):
                raise ValueError(f"cabecera existente no compatible: {target_header}; restaurar o revisar antes de seguir")
            if target_header.exists() and header != "StratosReporter_v11.mqh" and target_header.read_bytes() != source_header.read_bytes():
                if not args.refresh_reporter:
                    raise ValueError(f"adaptador existente distinto: {target_header}; restaurar o revisar antes de seguir")
                shutil.copy2(source_header, target_header)
                report["refreshed"].append(str(target_header))
            elif not target_header.exists():
                shutil.copy2(source_header, target_header)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> None:
    args = _parse_args()
    report = prepare(args)
    verb = "preparados" if args.apply else "validados en seco"
    print(f"G12: {len(report['prepared'])} EAs {verb}; {len(report['withheld'])} retenidos.")


if __name__ == "__main__":
    main()
