"""Extrae, en lectura, la identidad EA/gráfico desde perfiles MT5 `.chr`.

No muestra ni conserva parámetros ajenos a la identidad (por ejemplo tokens
de otros EAs). El manifiesto enlaza cada gráfico con nombre EA, magic y
comentario, y permite resolver copias históricas de `.ex5` sin heurística.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

IDENTITY_KEYS = {"name", "MagicNumber", "CustomComment", "symbol", "period"}


def _values(payload: bytes) -> dict[str, str]:
    text = payload.decode("utf-16", errors="ignore")
    values: dict[str, str] = {}
    for key, value in re.findall(r"(?m)^([A-Za-z][A-Za-z0-9_]*)=(.*)$", text):
        if key in IDENTITY_KEYS:
            # A chart can contain many historical trade objects with `name=`.
            # The first identity block is the EA attachment; later names are
            # chart objects and must not overwrite its executable filename.
            if key == "name" and key in values:
                continue
            values[key] = value.strip()
    return values


def _mt5_chart_id(payload: bytes) -> str | None:
    """Read only the root chart identifier, not IDs from drawing objects."""
    text = payload.decode("utf-16", errors="ignore")
    match = re.search(r"(?m)^id=([0-9]+)\r?$", text)
    return match.group(1) if match is not None else None


def _logical_charts(
    rows: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    """Collapse equivalent `.chr` serializations of one MT5 chart ID."""
    groups: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        chart_id = row.get("mt5_chart_id")
        key = str(chart_id) if chart_id not in (None, "") else str(row["chart_relative_path"])
        groups.setdefault(key, []).append(row)

    logical: list[dict[str, object]] = []
    serializations: list[dict[str, object]] = []
    conflicts: list[dict[str, object]] = []
    identity_fields = ("ea_filename", "magic_number", "comment_identity", "symbol")
    for chart_id, group in groups.items():
        fingerprint = {
            tuple(row.get(field) for field in identity_fields)
            for row in group
        }
        if len(fingerprint) != 1:
            logical.extend(group)
            conflicts.append(
                {
                    "mt5_chart_id": chart_id,
                    "chart_relative_paths": sorted(
                        str(row["chart_relative_path"]) for row in group
                    ),
                }
            )
            continue
        primary = min(group, key=lambda row: str(row["chart_relative_path"])).copy()
        paths = sorted(str(row["chart_relative_path"]) for row in group)
        primary["profile_serialization_paths"] = paths
        logical.append(primary)
        if len(group) > 1:
            serializations.append(
                {
                    "mt5_chart_id": chart_id,
                    "primary_chart_relative_path": primary["chart_relative_path"],
                    "duplicate_chart_relative_paths": paths[1:],
                    "identity": {
                        field: primary.get(field)
                        for field in identity_fields
                    },
                }
            )
    return logical, serializations, conflicts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bridge-root", type=Path, required=True)
    parser.add_argument("--terminal-alias", required=True)
    parser.add_argument("--account-login", required=True)
    parser.add_argument("--profile", default="Default")
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sys.path.insert(0, str(args.bridge_root))
    from config import resolver_terminal  # noqa: PLC0415
    from target import crear_target  # noqa: PLC0415

    target = crear_target(resolver_terminal(args.terminal_alias))
    root = f"Profiles/Charts/{args.profile}"
    rows: list[dict[str, object]] = []
    for entry in target.listar_dir(target.ruta_absoluta(root)):
        name = entry["nombre"]
        if entry["es_dir"] or not name.lower().endswith(".chr"):
            continue
        path = f"{root}/{name}"
        payload = target.leer_bytes(target.ruta_absoluta(path))
        values = _values(payload)
        if "MagicNumber" not in values and "CustomComment" not in values:
            continue
        rows.append(
            {
                "chart_relative_path": path,
                "mt5_chart_id": _mt5_chart_id(payload),
                "chart_sha256": hashlib.sha256(payload).hexdigest(),
                "ea_filename": values.get("name"),
                "magic_number": int(values["MagicNumber"])
                if values.get("MagicNumber", "").isdigit()
                else None,
                "comment_identity": values.get("CustomComment"),
                "symbol": values.get("symbol"),
                "period": values.get("period"),
            }
        )
    charts, duplicate_serializations, chart_id_conflicts = _logical_charts(rows)
    output = {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "account_login": args.account_login,
        "terminal_alias": args.terminal_alias,
        "profile": args.profile,
        "read_only": True,
        "charts": charts,
        "duplicate_profile_serializations": duplicate_serializations,
        "profile_chart_id_conflicts": chart_id_conflicts,
    }
    output["payload_sha256"] = hashlib.sha256(
        json.dumps(output, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {"output": str(args.output), "chart_identities": len(charts)}, ensure_ascii=False
        )
    )


if __name__ == "__main__":
    main()
