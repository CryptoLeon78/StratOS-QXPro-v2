"""Flujo guiado: Tester manual SQX_vs_MT5 -> archivo completo -> importación G13.

No controla cuentas reales ni adjunta EAs. Abre el panel local para que el operador
ejecute el Tester autorizado y, tras pulsar su botón de archivado, valida e importa
el paquete sellado. Sólo registra en la base cuando el informe contiene VEREDICTO.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ARCHIVE_SCHEMA = "sqx-vs-mt5-archive-v1"


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parents[1]
    return Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_archive(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != ARCHIVE_SCHEMA:
        raise ValueError("evidence-manifest no corresponde al archivo SQX_vs_MT5 v1.3.4")
    if not isinstance(payload.get("sqx_path"), str) or not isinstance(payload.get("verdict"), str):
        raise ValueError("evidence-manifest incompleto: faltan fuente SQX o veredicto")
    return payload


def _verified_artifact(archive_dir: Path, entries: list[dict[str, Any]], original_path: str) -> Path:
    expected_name = Path(original_path).name
    matches = [entry for entry in entries if entry.get("name") == expected_name]
    if len(matches) != 1:
        raise ValueError(f"artefacto archivado no resuelto de forma única: {expected_name}")
    path = archive_dir / expected_name
    if not path.is_file() or sha256_file(path) != matches[0].get("sha256"):
        raise ValueError(f"hash inválido o artefacto ausente: {expected_name}")
    return path


def resolve_import_inputs(archive_path: Path, inventory_path: Path) -> dict[str, Path]:
    archive = load_archive(archive_path)
    archive_dir = archive_path.parent
    sqx_path = Path(str(archive["sqx_path"]))
    if not sqx_path.is_file():
        raise ValueError(f"la fuente SQX original ya no está disponible: {sqx_path}")
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    matches = [
        item for item in inventory.get("items", [])
        if item.get("sqx_sha256") == sha256_file(sqx_path) and item.get("status") == "STATIC_VALIDATED"
    ]
    if len(matches) != 1:
        raise ValueError("el SQX archivado no tiene una pareja STATIC_VALIDATED única en el inventario")
    mq5_path = Path(str(matches[0]["mql5_path"]))
    if not mq5_path.is_file():
        raise ValueError(f"la pareja MQL5 inventariada ya no está disponible: {mq5_path}")
    artifacts = archive.get("artifacts")
    comparisons = archive.get("comparison_artifacts")
    if not isinstance(artifacts, list) or not isinstance(comparisons, list):
        raise ValueError("evidence-manifest sin listas de artefactos válidas")
    comparison_txt = [entry for entry in comparisons if str(entry.get("name", "")).lower().endswith(".txt")]
    if len(comparison_txt) != 1:
        raise ValueError("el archivo no contiene un informe TXT SQX_vs_MT5 único")
    comparison_path = archive_dir.parent / str(comparison_txt[0]["name"])
    if not comparison_path.is_file() or sha256_file(comparison_path) != comparison_txt[0].get("sha256"):
        raise ValueError("hash inválido o informe comparativo TXT ausente")
    return {
        "sqx": sqx_path,
        "mq5": mq5_path,
        "mt5_report": _verified_artifact(archive_dir, artifacts, str(archive["native_mt5_report"])),
        "tester_ini": _verified_artifact(archive_dir, artifacts, str(archive["tester_ini"])),
        "mt5_trades_csv": _verified_artifact(archive_dir, artifacts, str(archive["sqx_trades_csv"])),
        "comparison_report": comparison_path,
    }


def import_and_register(root: Path, archive_path: Path, *, register: bool) -> Path:
    inventory = root / "runtime" / "operational" / "analysis-inventory.json"
    inputs = resolve_import_inputs(archive_path, inventory)
    python = root / ".venv" / "Scripts" / "python.exe"
    importer = root / "scripts" / "import_manual_sqx_mt5_run.py"
    output = root / "runtime" / "operational" / "backtests_manual"
    command = [
        str(python), str(importer), "--inventory", str(inventory), "--sqx", str(inputs["sqx"]),
        "--mq5", str(inputs["mq5"]), "--mt5-report", str(inputs["mt5_report"]),
        "--tester-ini", str(inputs["tester_ini"]), "--mt5-trades-csv", str(inputs["mt5_trades_csv"]),
        "--comparison-report", str(inputs["comparison_report"]), "--output-root", str(output),
        "--terminal-id", "Darwinex MetaTrader 5",
    ]
    result = subprocess.run(command, cwd=root, text=True, check=True, capture_output=True)
    print(result.stdout, end="")
    manifest = next(
        (Path(token.split("=", 1)[1]) for token in result.stdout.split() if token.startswith("manifest=")),
        None,
    )
    if manifest is None or not manifest.is_file():
        raise ValueError("el importador no devolvió un manifiesto operativo")
    if register:
        relative = manifest.resolve().relative_to(root / "runtime" / "operational").as_posix()
        compose = [
            "docker", "compose", "-p", "stratos_operational", "-f", "docker-compose.yml",
            "-f", "docker-compose.operational.yml", "--env-file", ".env.operational", "run", "--rm",
            "-T", "--no-deps", "--volume", f"{root}:/workspace:ro",
            "--volume", f"{root / 'runtime' / 'operational'}:/runtime", "core-engine", "python",
            "/workspace/scripts/record_operational_backtest.py", "--manifest", f"/runtime/{relative}", "--apply",
        ]
        subprocess.run(compose, cwd=root, check=True)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-manifest", type=Path)
    parser.add_argument("--register", action="store_true", help="registra append-only tras importar")
    parser.add_argument("--open-panel", action="store_true", help="abre SQX_vs_MT5_Panel.exe antes de pedir el archivo")
    args = parser.parse_args()
    root = project_root()
    if args.open_panel:
        panel = root.parent / "SQX_vs_MT5_Panel" / "dist" / "SQX_vs_MT5_Panel.exe"
        if not panel.is_file():
            raise SystemExit(f"panel no encontrado: {panel}")
        subprocess.Popen([str(panel)], cwd=panel.parent)
        print("Panel abierto. Ejecuta el Tester y pulsa 'Archivar comparación + HTML MT5 + CSV'.")
    evidence = args.evidence_manifest
    if evidence is None:
        evidence = Path(input("Ruta completa de evidence-manifest.json: ").strip().strip('"'))
    manifest = import_and_register(root, evidence.resolve(), register=args.register)
    print(f"G13_IMPORT_OK manifest={manifest}")


if __name__ == "__main__":
    main()
