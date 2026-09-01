"""Asistente guiado y conservador para la admisión operacional de StratOS.

Este programa es el punto de entrada humano para candidatos de Análisis. No
envía órdenes, no modifica terminales reales y no adjunta EAs. Cada backtest
requiere una confirmación individual y su resultado se registra desde el
contenedor operacional como hecho append-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


LAUNCHER_VERSION = "stratos-operational-launcher-v1"
QUEUE_SNAPSHOT_VERSION = "operational-tester-queue-v1"


def project_root() -> Path:
    """Localiza la raíz tanto desde fuente como desde dist/StratOS_Operational.exe."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parents[1]
    return Path(__file__).resolve().parents[1]


def resolve_path(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


@dataclass(frozen=True)
class LauncherConfig:
    root: Path
    config_path: Path
    python_executable: Path
    env_file: Path
    compose_project: str
    compose_files: tuple[Path, ...]
    core_health_url: str
    analysis_root: Path
    projects_root: Path
    panel_dir: Path
    expected_terminal: str
    max_backtests_per_run: int
    core_health_startup_timeout_s: int


def load_config(root: Path, config_path: Path) -> LauncherConfig:
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(
            f"Falta la configuración local {config_path}. Copie "
            "config/operational_launcher.example.json y ajuste únicamente rutas locales."
        ) from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Configuración JSON inválida: {exc}") from exc
    if payload.get("version") != LAUNCHER_VERSION:
        raise ValueError("versión de configuración no compatible")

    required = (
        "python_executable", "env_file", "compose_project", "compose_files", "core_health_url",
        "analysis_root", "projects_root", "panel_dir", "expected_terminal", "max_backtests_per_run",
        "core_health_startup_timeout_s",
    )
    missing = [key for key in required if not payload.get(key)]
    if missing:
        raise ValueError(f"faltan claves de configuración: {', '.join(missing)}")
    compose_files = tuple(resolve_path(root, str(item)) for item in payload["compose_files"])
    if not isinstance(payload["max_backtests_per_run"], int) or not 1 <= payload["max_backtests_per_run"] <= 24:
        raise ValueError("max_backtests_per_run debe estar entre 1 y 24")
    if not isinstance(payload["core_health_startup_timeout_s"], int) or payload["core_health_startup_timeout_s"] < 1:
        raise ValueError("core_health_startup_timeout_s debe ser un entero positivo")
    env_file = resolve_path(root, str(payload["env_file"]))
    if env_file.name != ".env.operational":
        raise ValueError("el lanzador sólo admite el perfil .env.operational")
    config = LauncherConfig(
        root=root,
        config_path=config_path,
        python_executable=resolve_path(root, str(payload["python_executable"])),
        env_file=env_file,
        compose_project=str(payload["compose_project"]),
        compose_files=compose_files,
        core_health_url=str(payload["core_health_url"]),
        analysis_root=resolve_path(root, str(payload["analysis_root"])),
        projects_root=resolve_path(root, str(payload["projects_root"])),
        panel_dir=resolve_path(root, str(payload["panel_dir"])),
        expected_terminal=str(payload["expected_terminal"]),
        max_backtests_per_run=payload["max_backtests_per_run"],
        core_health_startup_timeout_s=payload["core_health_startup_timeout_s"],
    )
    for path, label in ((config.python_executable, "python_executable"), (config.env_file, "env_file"),
                        (config.analysis_root, "analysis_root"), (config.projects_root, "projects_root"),
                        (config.panel_dir, "panel_dir")):
        if not path.exists():
            raise ValueError(f"{label} no existe: {path}")
    for path in config.compose_files:
        if not path.is_file():
            raise ValueError(f"compose file inexistente: {path}")
    return config


def run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    print("\n> " + subprocess.list2cmdline(command))
    return subprocess.run(command, cwd=cwd, text=True, check=True)


def compose_base(config: LauncherConfig) -> list[str]:
    command = ["docker", "compose", "-p", config.compose_project]
    for compose_file in config.compose_files:
        command.extend(("-f", str(compose_file)))
    command.extend(("--env-file", str(config.env_file)))
    return command


def ensure_stack(config: LauncherConfig) -> None:
    run([*compose_base(config), "up", "-d"], cwd=config.root)
    deadline = time.monotonic() + config.core_health_startup_timeout_s
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(config.core_health_url, timeout=1) as response:
                if response.status == 200:
                    print("Stack operacional saludable.")
                    return
                last_error = ValueError(f"core health respondió HTTP {response.status}")
        except (urllib.error.URLError, OSError) as exc:
            last_error = exc
        time.sleep(1)
    raise ValueError(f"core operacional no saludable tras espera configurada: {last_error}")


def confirm(prompt: str) -> bool:
    return input(f"{prompt}\nEscriba SI para continuar: ").strip().upper() == "SI"


def python_script(config: LauncherConfig, script_name: str, *args: str) -> None:
    run([str(config.python_executable), str(config.root / "scripts" / script_name), *args], cwd=config.root)


def runtime_path(config: LauncherConfig, filename: str) -> Path:
    return config.root / "runtime" / "operational" / filename


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _queue_snapshot_path(config: LauncherConfig) -> Path:
    return runtime_path(config, "operational-tester-queue.json")


def _queue_events_path(config: LauncherConfig) -> Path:
    return runtime_path(config, "operational-tester-queue-events.jsonl")


def write_queue_snapshot(
    config: LauncherConfig, prefilter: Path, queue: list[dict[str, Any]], states: dict[int, str] | None = None,
) -> Path:
    """Publica el estado derivado de la cola, sin rutas locales ni secretos.

    Es una vista local, reemplazable y sellada. El historial inmutable vive en
    ``operational-tester-queue-events.jsonl``; la API sólo monta esta vista en
    lectura para que Pipeline no pueda ejecutar ni modificar el host Windows.
    """
    states = states or {}
    items = [
        {
            "rank": index,
            "strategy_name": str(item.get("strategy_name", "sin nombre")),
            "symbol": item.get("symbol"),
            "timeframe": item.get("timeframe"),
            "state": states.get(index, "PENDING_OPERATOR_CONFIRMATION"),
        }
        for index, item in enumerate(queue, start=1)
    ]
    body = {
        "version": QUEUE_SNAPSHOT_VERSION,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "prefilter_sha256": _sha256_bytes(prefilter.read_bytes()),
        "max_backtests_per_run": config.max_backtests_per_run,
        "entries": items,
    }
    encoded = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    body["snapshot_sha256"] = _sha256_bytes(encoded)
    target = _queue_snapshot_path(config)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def append_queue_event(config: LauncherConfig, *, rank: int, event: str, item: dict[str, Any], detail: str | None = None) -> None:
    """Añade evidencia append-only de cada presentación/decisión de Tester."""
    payload: dict[str, Any] = {
        "occurred_at_utc": datetime.now(UTC).isoformat(),
        "rank": rank,
        "event": event,
        "strategy_name": str(item.get("strategy_name", "sin nombre")),
        "symbol": item.get("symbol"),
        "timeframe": item.get("timeframe"),
    }
    if detail:
        payload["detail"] = detail
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["event_sha256"] = _sha256_bytes(canonical)
    path = _queue_events_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def apply_inventory(config: LauncherConfig, manifest: Path) -> None:
    runtime_dir = runtime_path(config, "").resolve()
    command = [
        *compose_base(config), "run", "--rm", "-T", "--no-deps",
        "--volume", f"{config.root}:/workspace:ro",
        "--volume", f"{runtime_dir}:/runtime",
        "core-engine", "python", "/workspace/scripts/operational_inventory.py",
        "--source-group", "ANALYSIS", "--manifest", f"/runtime/{manifest.name}",
        "--apply", "--apply-existing-manifest",
    ]
    run(command, cwd=config.root)


def refresh_pipeline(config: LauncherConfig) -> Path:
    inventory = runtime_path(config, "analysis-inventory.json")
    sources = runtime_path(config, "analysis-validation-sources.json")
    evidence = runtime_path(config, "analysis-validation-evidence.json")
    prefilter = runtime_path(config, "analysis-prefilter.json")
    python_script(config, "operational_inventory.py", "--root", str(config.analysis_root), "--source-group", "ANALYSIS", "--manifest", str(inventory))
    apply_inventory(config, inventory)
    python_script(config, "resolve_operational_validation_sources.py", "--inventory", str(inventory), "--projects-root", str(config.projects_root), "--output", str(sources))
    python_script(config, "extract_operational_validation_evidence.py", "--sources-manifest", str(sources), "--output", str(evidence))
    python_script(config, "operational_prefilter.py", "--inventory", str(inventory), "--quality-evidence", str(evidence), "--completed-backtests", str(config.root / "runtime" / "operational" / "backtests"), "--output", str(prefilter))
    return prefilter


def load_queue(prefilter: Path) -> list[dict[str, Any]]:
    payload = json.loads(prefilter.read_text(encoding="utf-8"))
    queue = payload.get("queue")
    if not isinstance(queue, list):
        raise ValueError("prefilter sin cola válida")
    return [item for item in queue if isinstance(item, dict)]


def persist_manifest(config: LauncherConfig, manifest: Path) -> None:
    relative = manifest.resolve().relative_to(runtime_path(config, "").resolve()).as_posix()
    runtime_dir = runtime_path(config, "").resolve()
    run([
        *compose_base(config), "run", "--rm", "-T", "--no-deps",
        "--volume", f"{config.root}:/workspace:ro", "--volume", f"{runtime_dir}:/runtime",
        "core-engine", "python", "/workspace/scripts/record_operational_backtest.py",
        "--manifest", f"/runtime/{relative}", "--apply",
    ], cwd=config.root)


def run_guided(config: LauncherConfig) -> None:
    ensure_stack(config)
    prefilter = refresh_pipeline(config)
    queue = load_queue(prefilter)[:config.max_backtests_per_run]
    states = {index: "PENDING_OPERATOR_CONFIRMATION" for index in range(1, len(queue) + 1)}
    write_queue_snapshot(config, prefilter, queue, states)
    print(f"\nCola disponible para esta ejecución: {len(queue)} candidato(s).")
    for index, item in enumerate(queue, start=1):
        name = item.get("strategy_name", "sin nombre")
        symbol = item.get("symbol", "—")
        timeframe = item.get("timeframe", "—")
        print(f"\n[{index}/{len(queue)}] {name} | {symbol} {timeframe}")
        append_queue_event(config, rank=index, event="PRESENTED_FOR_CONFIRMATION", item=item)
        if not confirm("¿Lanzar exclusivamente el Strategy Tester MT5 para este candidato?"):
            states[index] = "OPERATOR_SKIPPED"
            append_queue_event(config, rank=index, event="OPERATOR_SKIPPED", item=item)
            write_queue_snapshot(config, prefilter, queue, states)
            print("Omitido por el operador.")
            continue
        states[index] = "OPERATOR_CONFIRMED"
        append_queue_event(config, rank=index, event="OPERATOR_CONFIRMED", item=item)
        write_queue_snapshot(config, prefilter, queue, states)
        before = {path.resolve() for path in runtime_path(config, "backtests").glob("*/run-manifest.json")}
        try:
            python_script(
                config, "run_operational_sqx_mt5_backtest.py",
                "--panel-dir", str(config.panel_dir), "--sqx", str(item["sqx_path"]), "--mq5", str(item["mql5_path"]),
                "--output-root", str(runtime_path(config, "backtests")), "--expected-terminal", config.expected_terminal,
                "--allow-real-strategy-tester", "--manage-backtest-terminal", "--launch",
            )
        except subprocess.CalledProcessError as exc:
            states[index] = "TESTER_FAILED"
            append_queue_event(config, rank=index, event="TESTER_FAILED", item=item, detail=str(exc))
            write_queue_snapshot(config, prefilter, queue, states)
            raise
        after = {path.resolve() for path in runtime_path(config, "backtests").glob("*/run-manifest.json")}
        created = sorted(after - before)
        if len(created) != 1:
            states[index] = "MANIFEST_UNRESOLVED"
            append_queue_event(config, rank=index, event="MANIFEST_UNRESOLVED", item=item)
            write_queue_snapshot(config, prefilter, queue, states)
            raise ValueError("no se pudo identificar un único manifiesto de la corrida MT5")
        persist_manifest(config, created[0])
        states[index] = "SEALED_AND_REGISTERED"
        append_queue_event(config, rank=index, event="SEALED_AND_REGISTERED", item=item,
                           detail=_sha256_bytes(created[0].read_bytes()))
        write_queue_snapshot(config, prefilter, queue, states)
        print(f"Backtest sellado y registrado: {created[0]}")
    print("\nIncubación: BLOQUEADA. No hay integración operativa demo configurada en este ejecutable; ningún EA se adjuntó ni se envió orden alguna.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, help="raíz de StratOS-QXPro-v2")
    parser.add_argument("--config", type=Path, help="JSON local; por defecto runtime/operational/launcher.json")
    parser.add_argument("--refresh-only", action="store_true", help="actualiza inventario/evidencia/prefiltro sin abrir MT5")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = (args.project_root or project_root()).resolve()
    config_path = (args.config or root / "runtime" / "operational" / "launcher.json").resolve()
    try:
        config = load_config(root, config_path)
        if args.refresh_only:
            ensure_stack(config)
            prefilter = refresh_pipeline(config)
            queue = load_queue(prefilter)[:config.max_backtests_per_run]
            snapshot = write_queue_snapshot(config, prefilter, queue)
            print(f"Prefiltro actualizado: {prefilter}")
            print(f"Cola local sellada: {snapshot}")
        else:
            run_guided(config)
    except (ValueError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"BLOQUEADO: {exc}") from exc


if __name__ == "__main__":
    main()
