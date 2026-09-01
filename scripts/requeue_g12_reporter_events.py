"""Permite reprocesar JSONL G12 ya conservados tras corregir el conector.

Sólo elimina las marcas locales ``reporter_event:`` del buffer SQLite. Los
JSONL del EA no se modifican; el core mantiene su propia deduplicación por
sello y el estado de EA se persiste como UPSERT.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


def requeue(buffer_path: Path, report_path: Path, apply: bool) -> dict[str, object]:
    if buffer_path.name != "connector-buffer.sqlite":
        raise ValueError("sólo se admite el buffer G12 connector-buffer.sqlite")
    if not buffer_path.is_file():
        raise ValueError(f"buffer no encontrado: {buffer_path}")
    with sqlite3.connect(buffer_path) as connection:
        before = int(connection.execute("SELECT COUNT(*) FROM meta WHERE key LIKE 'reporter_event:%'").fetchone()[0])
        if apply:
            connection.execute("DELETE FROM meta WHERE key LIKE 'reporter_event:%'")
            connection.commit()
        after = int(connection.execute("SELECT COUNT(*) FROM meta WHERE key LIKE 'reporter_event:%'").fetchone()[0])
    payload: dict[str, object] = {
        "ok": True,
        "mode": "apply" if apply else "dry_run",
        "reporter_dedup_keys_before": before,
        "reporter_dedup_keys_after": after,
        "outbox_jsonl_modified": False,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--buffer", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    payload = requeue(args.buffer, args.report, args.apply)
    print(f"G12 reporter: {payload['reporter_dedup_keys_before']} marcas; modo={payload['mode']}")


if __name__ == "__main__":
    main()
