"""Instala y compila exclusivamente los indicadores custom requeridos por los EAs G12 READY."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any


ICUSTOM_NAME = re.compile(r'iCustom\s*\([^;]*?"(Sq[A-Za-z0-9_]+)"', re.DOTALL)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def required_indicators(manifest: dict[str, Any], terminal_data_root: Path) -> list[str]:
    names: set[str] = set()
    experts_dir = terminal_data_root / "MQL5" / "Experts" / "StratOS_G12"
    for candidate in manifest.get("candidates", []):
        if candidate.get("status") != "READY":
            continue
        source = experts_dir / f"{candidate['strategy_name']}.mq5"
        if not source.is_file():
            raise ValueError(f"falta EA G12 instrumentado: {source}")
        names.update(ICUSTOM_NAME.findall(source.read_text(encoding="utf-8", errors="ignore")))
    if not names:
        raise ValueError("no se detectaron indicadores Sq* en los EAs READY")
    return sorted(names)


def _copy_indicator(source: Path, target: Path, resume: bool) -> str:
    if target.exists():
        if _sha256(source) != _sha256(target):
            if not resume:
                raise ValueError(f"indicador existente distinto: {target}; usar --resume sólo tras revisar el origen")
            shutil.copy2(source, target)
            return "refreshed"
        return "already_identical"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return "installed"


def install(args: argparse.Namespace) -> dict[str, Any]:
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    names = required_indicators(manifest, args.terminal_data_root)
    target_dir = args.terminal_data_root / "MQL5" / "Indicators"
    records: list[dict[str, Any]] = []
    for name in names:
        source = args.indicator_source_root / f"{name}.mq5"
        target = target_dir / source.name
        if not source.is_file():
            raise ValueError(f"no existe fuente del indicador requerido {name}: {source}")
        action = "planned"
        if args.apply:
            action = _copy_indicator(source, target, args.resume)
        records.append({"name": name, "source": str(source), "target": str(target), "action": action})
    payload = {
        "ok": True,
        "mode": "apply" if args.apply else "dry_run",
        "compiled": False,
        "compile_next_action": "run scripts/compile_g12_mt5_indicators.ps1 from native PowerShell; MetaEditor must receive /compile:\"path\"",
        "required_count": len(records),
        "indicators": records,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--terminal-data-root", required=True, type=Path)
    parser.add_argument("--indicator-source-root", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def main() -> None:
    payload = install(parse_args())
    print(f"G12 MT5: {payload['required_count']} indicadores {'instalados' if payload['mode'] == 'apply' else 'validados en seco'}.")


if __name__ == "__main__":
    main()
