"""Resuelve la procedencia SQX de cada candidato contra proyectos locales.

La asociación automática exige un hash idéntico del .sqx de Análisis dentro
de un único proyecto SQX. Los artefactos de WFM/MC/OOS se enumeran y sellan
por su identidad de estrategia, pero no se convierten en un veredicto ni se
confunde una coincidencia de nombre con una validación aprobada.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

STRATEGY_IDENTIFIER_PATTERN = re.compile(r"strategy\s+(\d+(?:\.\d+)+)", re.IGNORECASE)
HISTORY_SIGNATURE_MEMBERS = ("orders.bin", "lastSettings.xml")


def sha256_file(path: Path, cache: dict[Path, str]) -> str:
    resolved = path.resolve()
    if resolved not in cache:
        cache[resolved] = hashlib.sha256(resolved.read_bytes()).hexdigest()
    return cache[resolved]


def seal_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_json_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON objeto requerido: {path}")
    return data


def load_layout(path: Path) -> dict[str, str]:
    data = load_json_object(path)
    keys = (
        "version",
        "project_name_prefix",
        "project_definition_filename",
        "databanks_directory_name",
        "strategy_extension",
    )
    missing = [key for key in keys if not isinstance(data.get(key), str) or not data[key]]
    if missing:
        raise ValueError(f"layout incompleto: {', '.join(missing)}")
    return {key: str(data[key]) for key in keys}


def strategy_identifier(path: Path) -> str | None:
    match = STRATEGY_IDENTIFIER_PATTERN.search(path.stem)
    return match.group(1) if match else None


def project_identity(project: Path, layout: dict[str, str]) -> str:
    name = project.name
    prefix = layout["project_name_prefix"]
    if name.casefold().startswith(prefix.casefold()):
        name = name[len(prefix) :]
    return name.casefold()


def source_lineage_hints(sqx_path: Path, source_root: str | None) -> list[str]:
    if not source_root:
        return []
    try:
        relative = sqx_path.resolve().relative_to(Path(source_root).resolve())
    except ValueError:
        return []
    return [part.casefold() for part in relative.parts[:-1]]


def history_signature(path: Path, cache: dict[Path, str | None]) -> str | None:
    """Identidad de evidencia SQX estable ante cambios de metadatos de exportación.

    ``strategy_Portfolio.xml`` y ``settings.xml`` pueden cambiar al reexportar
    una estrategia. El resultado histórico reproducible queda anclado por los
    órdenes y los ajustes de la corrida, sin inferir equivalencia de código.
    """
    resolved = path.resolve()
    if resolved in cache:
        return cache[resolved]
    try:
        with zipfile.ZipFile(resolved) as archive:
            if not set(HISTORY_SIGNATURE_MEMBERS).issubset(archive.namelist()):
                cache[resolved] = None
                return None
            members = {
                member: hashlib.sha256(archive.read(member)).hexdigest()
                for member in HISTORY_SIGNATURE_MEMBERS
            }
    except (OSError, zipfile.BadZipFile):
        cache[resolved] = None
        return None
    cache[resolved] = seal_payload(members)
    return cache[resolved]


def candidate_rows(
    inventory: dict[str, Any], hash_cache: dict[Path, str], signature_cache: dict[Path, str | None]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in inventory.get("items", []):
        if item.get("status") != "STATIC_VALIDATED" or not isinstance(item.get("sqx_path"), str):
            continue
        sqx_path = Path(item["sqx_path"])
        if not sqx_path.is_file():
            continue
        digest = sha256_file(sqx_path, hash_cache)
        if digest != item.get("sqx_sha256"):
            continue
        rows.append(
            {
                "strategy_name": item.get("strategy_name"),
                "sqx_path": str(sqx_path.resolve()),
                "sqx_sha256": digest,
                "mql5_path": item.get("mql5_path"),
                "mql5_sha256": item.get("mql5_sha256"),
                "symbol": item.get("symbol"),
                "timeframe": item.get("timeframe"),
                "strategy_identifier": strategy_identifier(sqx_path),
                "history_signature": history_signature(sqx_path, signature_cache),
                "source_lineage_hints": source_lineage_hints(sqx_path, item.get("source_root")),
            }
        )
    return rows


def project_dirs(projects_root: Path, layout: dict[str, str]) -> list[Path]:
    return sorted(
        path
        for path in projects_root.iterdir()
        if path.is_dir() and (path / layout["project_definition_filename"]).is_file()
    )


def artifact_entry(path: Path, databanks_root: Path, hash_cache: dict[Path, str]) -> dict[str, str]:
    relative = path.relative_to(databanks_root)
    bucket = relative.parts[0] if relative.parts else ""
    return {
        "path": str(path.resolve()),
        "sha256": sha256_file(path, hash_cache),
        "databank_bucket": bucket,
    }


def resolve_sources(
    inventory: dict[str, Any], *, projects_root: Path, layout: dict[str, str]
) -> list[dict[str, Any]]:
    hash_cache: dict[Path, str] = {}
    signature_cache: dict[Path, str | None] = {}
    candidates = candidate_rows(inventory, hash_cache, signature_cache)
    by_hash = {row["sqx_sha256"]: row for row in candidates}
    by_signature: dict[str, list[str]] = defaultdict(list)
    for row in candidates:
        if row["history_signature"]:
            by_signature[str(row["history_signature"])].append(str(row["sqx_sha256"]))
    identifiers = {row["strategy_identifier"] for row in candidates if row["strategy_identifier"]}
    exact_projects: dict[str, set[Path]] = defaultdict(set)
    matched_artifacts: dict[str, list[dict[str, str]]] = defaultdict(list)

    for project in project_dirs(projects_root, layout):
        databanks = project / layout["databanks_directory_name"]
        if not databanks.is_dir():
            continue
        for artifact in databanks.rglob(f"*{layout['strategy_extension']}"):
            identifier = strategy_identifier(artifact)
            if identifier not in identifiers:
                continue
            digest = sha256_file(artifact, hash_cache)
            matches: dict[str, str] = {}
            if digest in by_hash:
                matches[digest] = "EXACT_SHA256"
            signature = history_signature(artifact, signature_cache)
            if signature:
                for candidate_hash in by_signature.get(signature, []):
                    matches.setdefault(candidate_hash, "SQX_HISTORY_SIGNATURE")
            for candidate_hash, match_type in matches.items():
                exact_projects[candidate_hash].add(project)
                entry = artifact_entry(artifact, databanks, hash_cache)
                entry["match_type"] = match_type
                matched_artifacts[candidate_hash].append(entry)

    resolved: list[dict[str, Any]] = []
    for candidate in candidates:
        digest = candidate["sqx_sha256"]
        projects = sorted(exact_projects.get(digest, set()))
        matching_projects = list(projects)
        result = dict(candidate)
        if not candidate["strategy_identifier"]:
            result.update({"status": "WITHHELD", "reason": "NO_STRATEGY_IDENTIFIER"})
            resolved.append(result)
            continue
        if not projects:
            result.update({"status": "WITHHELD", "reason": "NO_PROJECT_HASH_MATCH"})
            resolved.append(result)
            continue
        source_selection = "UNIQUE_HISTORY_SIGNATURE"
        if len(projects) > 1:
            lineage_projects = [
                project
                for project in projects
                if project_identity(project, layout) in candidate["source_lineage_hints"]
            ]
            if len(lineage_projects) == 1:
                projects = lineage_projects
                source_selection = "HISTORY_SIGNATURE_PLUS_SOURCE_LINEAGE"
        if len(projects) != 1:
            result.update(
                {
                    "status": "WITHHELD",
                    "reason": "AMBIGUOUS_PROJECT_HASH_MATCH",
                    "candidate_projects": [str(path.resolve()) for path in projects],
                }
            )
            resolved.append(result)
            continue

        project = projects[0]
        databanks = project / layout["databanks_directory_name"]
        identifier = str(candidate["strategy_identifier"])
        validations = [
            artifact_entry(artifact, databanks, hash_cache)
            for artifact in sorted(databanks.rglob(f"*{layout['strategy_extension']}"))
            if strategy_identifier(artifact) == identifier
        ]
        definition = project / layout["project_definition_filename"]
        result.update(
            {
                "status": "RESOLVED",
                "source_selection": source_selection,
                "project_path": str(project.resolve()),
                "history_signature_projects": [
                    str(path.resolve()) for path in matching_projects
                ],
                "project_definition": {
                    "path": str(definition.resolve()),
                    "sha256": sha256_file(definition, hash_cache),
                },
                "source_matches": sorted(
                    (
                        item
                        for item in matched_artifacts[digest]
                        if Path(item["path"]).is_relative_to(databanks)
                    ),
                    key=lambda item: item["path"],
                ),
                "validation_artifacts": validations,
            }
        )
        resolved.append(result)
    return resolved


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--projects-root", type=Path, required=True)
    parser.add_argument(
        "--layout", type=Path, default=Path("config/operational_source_resolution.json")
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.projects_root.is_dir():
        raise SystemExit(f"projects root inexistente: {args.projects_root}")

    inventory = load_json_object(args.inventory)
    layout = load_layout(args.layout)
    rows = resolve_sources(inventory, projects_root=args.projects_root, layout=layout)
    payload = {
        "version": layout["version"],
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "inventory": {"path": str(args.inventory.resolve())},
        "projects_root": str(args.projects_root.resolve()),
        "layout": {"path": str(args.layout.resolve())},
        "summary": {
            "candidates": len(rows),
            "resolved": sum(row["status"] == "RESOLVED" for row in rows),
            "withheld": sum(row["status"] == "WITHHELD" for row in rows),
        },
        "items": rows,
    }
    payload["manifest_sha256"] = seal_payload(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"source_resolution resolved={payload['summary']['resolved']} "
        f"withheld={payload['summary']['withheld']} output={args.output}"
    )


if __name__ == "__main__":
    main()
