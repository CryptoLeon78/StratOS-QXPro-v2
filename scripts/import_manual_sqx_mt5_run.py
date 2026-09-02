"""Sella e importa evidencia manual de SQX_vs_MT5 sin abrir MetaTrader 5.

Un informe nativo de MT5 demuestra que el Tester terminó, pero por sí solo no
demuestra una comparación SQX↔MT5. Este importador copia la evidencia a un
directorio operacional inmutable, verifica la identidad contra el inventario
sellado y crea un manifiesto idempotente. Sólo un informe de comparación que
incluya un veredicto permite el registro append-only posterior.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


MANIFEST_NAME = "run-manifest.json"
VERDICT_PATTERN = re.compile(r"VEREDICTO:\s*(VALIDADA|TOLERABLE|DISCREPANTE)")
DATE_RANGE_PATTERN = re.compile(
    r"\b([0-9]{4})[.\-]([0-9]{2})[.\-]([0-9]{2})\s*-\s*"
    r"([0-9]{4})[.\-]([0-9]{2})[.\-]([0-9]{2})\b"
)
IMAGE_SOURCE_PATTERN = re.compile(r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"']", re.IGNORECASE)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seal_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _normalise_symbol(symbol: str) -> str:
    return re.sub(r"_darwinex$", "", symbol, flags=re.IGNORECASE).casefold()


def _date_from_match(groups: tuple[str, ...], offset: int) -> str:
    return f"{groups[offset]}-{groups[offset + 1]}-{groups[offset + 2]}"


def _load_inventory_entry(inventory_path: Path, sqx_path: Path, mq5_path: Path) -> dict[str, Any]:
    payload = json.loads(inventory_path.read_text(encoding="utf-8"))
    sqx_hash = sha256_file(sqx_path)
    mq5_hash = sha256_file(mq5_path)
    matches = [
        item
        for item in payload.get("items", [])
        if item.get("sqx_sha256") == sqx_hash and item.get("mql5_sha256") == mq5_hash
    ]
    if len(matches) != 1:
        raise ValueError("fuente SQX/MQL5 no resuelta de forma única en el inventario operacional")
    entry = matches[0]
    if entry.get("status") != "STATIC_VALIDATED":
        raise ValueError("la fuente no tiene estado STATIC_VALIDATED en el inventario operacional")
    return entry


def _report_text(report_path: Path) -> str:
    raw = report_path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")) or raw.count(b"\x00") > len(raw) // 4:
        return html.unescape(raw.decode("utf-16", errors="replace"))
    return html.unescape(raw.decode("utf-8", errors="replace"))


def _validate_report_identity(report_path: Path, entry: dict[str, Any]) -> tuple[str, str]:
    text = _report_text(report_path)
    strategy_name = str(entry["strategy_name"])
    if strategy_name not in text:
        raise ValueError("el informe MT5 no acredita el nombre exacto de estrategia del inventario")
    symbol = _normalise_symbol(str(entry["symbol"]))
    if not re.search(rf"\b{re.escape(symbol)}\b", text, flags=re.IGNORECASE):
        raise ValueError("el informe MT5 no acredita el símbolo del inventario")
    timeframe = str(entry["timeframe"])
    if not re.search(rf"\b{re.escape(timeframe)}\b", text, flags=re.IGNORECASE):
        raise ValueError("el informe MT5 no acredita el timeframe del inventario")
    match = DATE_RANGE_PATTERN.search(text)
    if match is None:
        raise ValueError("el informe MT5 no declara una ventana temporal verificable")
    groups = match.groups()
    return _date_from_match(groups, 0), _date_from_match(groups, 3)


def _report_sidecars(report_path: Path) -> list[Path]:
    text = _report_text(report_path)
    sidecars: list[Path] = []
    for raw_name in IMAGE_SOURCE_PATTERN.findall(text):
        candidate = report_path.parent / Path(raw_name).name
        if candidate.is_file() and candidate.resolve().parent == report_path.parent.resolve():
            sidecars.append(candidate)
    return sorted(set(sidecars), key=lambda path: path.name.casefold())


def _copy_immutable(source: Path, destination: Path) -> None:
    if destination.exists():
        if not destination.is_file() or sha256_file(source) != sha256_file(destination):
            raise ValueError(f"colisión de artefacto existente: {destination}")
        return
    shutil.copy2(source, destination)


def _artifact_entry(path: Path) -> dict[str, str]:
    return {"name": path.name, "path": str(path), "sha256": sha256_file(path)}


def import_manual_run(
    *,
    inventory_path: Path,
    sqx_path: Path,
    mq5_path: Path,
    mt5_report: Path,
    output_root: Path,
    terminal_id: str,
    tester_ini: Path | None = None,
    mt5_trades_csv: Path | None = None,
    comparison_report: Path | None = None,
) -> tuple[Path, str]:
    """Copia y sella una corrida manual, sin arrancar MT5 ni modificar fuentes."""
    required_files = [inventory_path, sqx_path, mq5_path, mt5_report]
    optional_files = [path for path in (tester_ini, mt5_trades_csv, comparison_report) if path]
    for path in required_files + optional_files:
        if not path.is_file():
            raise ValueError(f"artefacto requerido inexistente: {path}")
    entry = _load_inventory_entry(inventory_path, sqx_path, mq5_path)
    since, until = _validate_report_identity(mt5_report, entry)
    comparison_text = comparison_report.read_text(encoding="utf-8", errors="replace") if comparison_report else ""
    verdict_match = VERDICT_PATTERN.search(comparison_text)
    if comparison_report and verdict_match is None:
        raise ValueError("el informe de comparación no contiene un veredicto SQX_vs_MT5 reconocible")

    evidence_sources = [mt5_report, *_report_sidecars(mt5_report), *optional_files]
    evidence_hash = seal_payload(
        {
            "sqx_sha256": sha256_file(sqx_path),
            "mq5_sha256": sha256_file(mq5_path),
            "evidence": [{"name": path.name, "sha256": sha256_file(path)} for path in evidence_sources],
        }
    )
    output_dir = output_root / f"manual_{evidence_hash[:12]}_{sha256_file(sqx_path)[:12]}"
    manifest_path = output_dir / MANIFEST_NAME
    if manifest_path.is_file():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing.get("evidence_sha256") == evidence_hash:
            return manifest_path, "already_imported"
        raise ValueError("colisión de directorio manual con una evidencia distinta")

    output_dir.mkdir(parents=True, exist_ok=False)
    copied: list[Path] = []
    for source in evidence_sources:
        destination = output_dir / source.name
        _copy_immutable(source, destination)
        copied.append(destination)

    mode = "launch" if verdict_match else "manual_report_only"
    payload: dict[str, Any] = {
        "run_id": f"manual_{evidence_hash[:12]}",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "mode": mode,
        "execution_origin": "MANUAL_SQX_VS_MT5_IMPORT",
        "evidence_sha256": evidence_hash,
        "terminal": {"id": terminal_id, "algotrading": False, "is_real": True},
        "source": {
            "sqx_path": str(sqx_path.resolve()),
            "mq5_path": str(mq5_path.resolve()),
            "sqx_sha256": sha256_file(sqx_path),
            "mq5_sha256": sha256_file(mq5_path),
            "inventory_status": entry["status"],
        },
        "range": {"from": since, "to": until, "real_ticks_required": True},
        "strategy": {
            "name": entry["strategy_name"],
            "symbol": entry["symbol"],
            "timeframe": entry["timeframe"],
            "magic_number": entry.get("magic_number"),
        },
        "artifacts": [_artifact_entry(path) for path in copied],
    }
    if verdict_match:
        payload["result"] = {
            "returncode": 0,
            "stdout": comparison_text,
            "stderr": "",
            "verdict": verdict_match.group(1),
        }
    else:
        payload["result"] = {
            "returncode": 0,
            "stdout": "MANUAL_MT5_REPORT_ONLY: falta informe de comparación SQX_vs_MT5 con veredicto.",
            "stderr": "",
        }
    payload["manifest_sha256"] = seal_payload(payload)
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path, "comparison_ready" if verdict_match else "report_only"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--sqx", type=Path, required=True)
    parser.add_argument("--mq5", type=Path, required=True)
    parser.add_argument("--mt5-report", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--terminal-id", required=True)
    parser.add_argument("--tester-ini", type=Path)
    parser.add_argument("--mt5-trades-csv", type=Path)
    parser.add_argument("--comparison-report", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest_path, result = import_manual_run(
        inventory_path=args.inventory.resolve(),
        sqx_path=args.sqx.resolve(),
        mq5_path=args.mq5.resolve(),
        mt5_report=args.mt5_report.resolve(),
        output_root=args.output_root.resolve(),
        terminal_id=args.terminal_id,
        tester_ini=args.tester_ini.resolve() if args.tester_ini else None,
        mt5_trades_csv=args.mt5_trades_csv.resolve() if args.mt5_trades_csv else None,
        comparison_report=args.comparison_report.resolve() if args.comparison_report else None,
    )
    print(f"import={result} manifest={manifest_path}")
    if result == "report_only":
        print("registration=not_attempted reason=missing_comparison_verdict")


if __name__ == "__main__":
    main()
