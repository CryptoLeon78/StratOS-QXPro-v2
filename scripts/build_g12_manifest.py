"""Audita los supervivientes G12 sin modificar archivos de origen ni la base."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.services.sqx_baseline_parser import parse_sqx144_baseline


MAGIC_PATTERN = re.compile(r"\bMagicNumber\s*=\s*(\d+)\s*;")
ARTIFACT_EXTENSIONS = (".sqx", ".mq5", ".ex5")


@dataclass(frozen=True)
class ArtifactSelection:
    sqx: Path | None
    mq5: Path | None
    ex5: Path | None


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _select(paths: list[Path], preferred_path_contains: str) -> Path | None:
    if not paths:
        return None
    normalized_preference = preferred_path_contains.replace("\\", "/").lower()
    preferred = [
        path for path in paths if normalized_preference in path.as_posix().lower()
    ]
    return sorted(preferred or paths, key=lambda path: str(path).lower())[0]


def index_artifacts(
    root: Path, strategy_names: set[str], paths_file: Path | None = None
) -> dict[str, list[Path]]:
    """Recorre el archivo histórico una sola vez, incluso para campañas amplias."""
    indexed = {name: [] for name in strategy_names}
    if paths_file is not None:
        # El índice ya fue construido con Path.is_file() en el host. Evitar
        # 100k llamadas de metadata a través del montaje Windows→Docker.
        for relative_path in paths_file.read_text(encoding="utf-8").splitlines():
            path = root / relative_path
            if path.stem in indexed:
                indexed[path.stem].append(path)
        return indexed
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in ARTIFACT_EXTENSIONS and path.stem in indexed:
            indexed[path.stem].append(path)
    return indexed


def find_artifacts(matches: list[Path], preferred_path_contains: str) -> ArtifactSelection:
    return ArtifactSelection(
        sqx=_select([path for path in matches if path.suffix.lower() == ".sqx"], preferred_path_contains),
        mq5=_select([path for path in matches if path.suffix.lower() == ".mq5"], preferred_path_contains),
        ex5=_select([path for path in matches if path.suffix.lower() == ".ex5"], preferred_path_contains),
    )


def parse_magic(mq5: Path) -> int:
    match = MAGIC_PATTERN.search(mq5.read_text(encoding="utf-8", errors="ignore"))
    if match is None:
        raise ValueError("MagicNumber no encontrado en el fuente MQL5")
    return int(match.group(1))


def _identity_mismatch(candidate: dict[str, Any], *, symbol: str, timeframe: str) -> str | None:
    if symbol != candidate["darwinex_symbol"]:
        return (
            "símbolo SQX no coincide con el símbolo Darwinex esperado: "
            f"{symbol} != {candidate['darwinex_symbol']}"
        )
    if timeframe != candidate["timeframe"]:
        return (
            "timeframe SQX no coincide con el timeframe esperado: "
            f"{timeframe} != {candidate['timeframe']}"
        )
    return None


def candidate_report(candidate: dict[str, Any], indexed: dict[str, list[Path]]) -> dict[str, Any]:
    artifacts = find_artifacts(indexed[candidate["strategy_name"]], candidate["preferred_path_contains"])
    report: dict[str, Any] = {**candidate, "status": "WITHHELD", "reasons": []}
    if artifacts.sqx is None:
        report["reasons"].append("falta artefacto .sqx exacto")
    if artifacts.mq5 is None:
        report["reasons"].append("falta fuente .mq5 exacto")
    if artifacts.sqx is None or artifacts.mq5 is None:
        return report
    try:
        parsed = parse_sqx144_baseline(artifacts.sqx.read_bytes())
    except ValueError as exc:
        report["reasons"].append(f"SQX144 inválido: {exc}")
        return report
    if mismatch := _identity_mismatch(
        candidate, symbol=parsed.symbol, timeframe=parsed.timeframe
    ):
        report["reasons"].append(mismatch)
        return report
    try:
        magic_number = parse_magic(artifacts.mq5)
    except ValueError as exc:
        report["reasons"].append(str(exc))
        return report
    report.update(
        {
            "status": "READY",
            "sqx_path": str(artifacts.sqx),
            "sqx_sha256": sha256(artifacts.sqx),
            "mq5_path": str(artifacts.mq5),
            "mq5_sha256": sha256(artifacts.mq5),
            "ex5_path": str(artifacts.ex5) if artifacts.ex5 else None,
            "ex5_sha256": sha256(artifacts.ex5) if artifacts.ex5 else None,
            "magic_number": magic_number,
            "sqx": {
                "build": parsed.build,
                "symbol": parsed.symbol,
                "timeframe": parsed.timeframe,
                "backtest_from": parsed.backtest_from,
                "backtest_to": parsed.backtest_to,
                "trade_count": parsed.trade_count,
            },
        }
    )
    return report


def build_manifest(config: dict[str, Any], ea_root: Path, paths_file: Path | None = None) -> dict[str, Any]:
    indexed = index_artifacts(
        ea_root, {candidate["strategy_name"] for candidate in config["candidates"]}, paths_file
    )
    reports = [candidate_report(candidate, indexed) for candidate in config["candidates"]]
    seen_magics: dict[int, str] = {}
    for report in reports:
        magic = report.get("magic_number")
        if report["status"] != "READY" or magic is None:
            continue
        existing = seen_magics.get(magic)
        if existing is not None:
            report["status"] = "WITHHELD"
            report["reasons"].append(f"magic duplicado con {existing}")
        else:
            seen_magics[magic] = report["strategy_name"]
    return {
        "schema_version": config["schema_version"],
        "ea_required_version": config["ea_required_version"],
        "source_root": str(ea_root.resolve()),
        "candidates": reports,
        "ready_count": sum(report["status"] == "READY" for report in reports),
        "withheld_count": sum(report["status"] != "READY" for report in reports),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("config/g12_survivors.json"))
    parser.add_argument("--ea-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--paths-file", type=Path, help="índice relativo creado en el host Windows")
    parser.add_argument("--strict", action="store_true", help="falla si queda algún candidato retenido")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    manifest = build_manifest(config, args.ea_root, args.paths_file)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"G12 manifest: {manifest['ready_count']} READY, {manifest['withheld_count']} WITHHELD")
    if args.strict and manifest["withheld_count"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
