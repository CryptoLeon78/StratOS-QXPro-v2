"""Snapshot no destructivo de los únicos destinos MT5 que G12 puede modificar."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--terminal-data-root", required=True, type=Path)
    parser.add_argument("--backup-root", required=True, type=Path)
    args = parser.parse_args()
    sources = {
        "experts_stratos_g12": args.terminal_data_root / "MQL5" / "Experts" / "StratOS_G12",
        "include_stratos": args.terminal_data_root / "MQL5" / "Include" / "StratOS",
    }
    report: dict[str, object] = {"terminal": str(args.terminal_data_root), "entries": {}}
    for label, source in sources.items():
        destination = args.backup_root / label
        if not source.exists():
            report["entries"][label] = {"status": "ABSENT"}
            continue
        if destination.exists():
            raise SystemExit(f"backup ya existe: {destination}; no se sobrescribe")
        shutil.copytree(source, destination)
        files = [path for path in destination.rglob("*") if path.is_file()]
        report["entries"][label] = {
            "status": "COPIED",
            "files": {str(path.relative_to(destination)): _hash(path) for path in files},
        }
    args.backup_root.mkdir(parents=True, exist_ok=True)
    (args.backup_root / "manifest.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Backup G12 creado en {args.backup_root}")


if __name__ == "__main__":
    main()
