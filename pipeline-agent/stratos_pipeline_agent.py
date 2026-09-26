"""Agente residente de Pipeline para la sesión interactiva de Contabo.

No usa SSH ni conoce cuentas reales. Su configuración local define exactamente
los roles Tester e Incubadora demo que acepta; cualquier otro comando falla.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

import yaml

_EXECUTABLE_ROLES = {"ANALYSIS", "SQX_VS_MT5_TESTER", "CONTABO_INCUBATOR_DEMO"}
_REAL_ROLES = {"JJTI", "BEPB"}
_MAGIC_PATTERN = re.compile(r"^MagicNumber=(\d+)\s*$", re.MULTILINE)
_MANIFEST_PATTERN = re.compile(r"manifest=([^\r\n]+)")


def scan_incubator_charts(data_root: Path, active_profile: str) -> dict[int, list[Path]]:
    """Read only the active Incubadora profile before adding another chart.

    Recovery profiles are intentionally allowed to contain the same magics as the
    active profile.  Treating every profile as live would make preservation fail
    closed forever after a legitimate recovery snapshot.
    """
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,96}", active_profile):
        raise ValueError("incubator active_profile is invalid")
    charts_root = data_root / "MQL5" / "Profiles" / "Charts" / active_profile
    observed: dict[int, list[Path]] = {}
    for chart in charts_root.rglob("*.chr") if charts_root.is_dir() else []:
        try:
            contents = chart.read_text(encoding="utf-16")
        except UnicodeError as exc:
            raise ValueError(f"cannot read chart serialization: {chart}") from exc
        for magic in _MAGIC_PATTERN.findall(contents):
            observed.setdefault(int(magic), []).append(chart)
    return observed


def assert_existing_incubator_identity(target: dict[str, Any]) -> dict[int, list[Path]]:
    expected = target.get("preserve_magics")
    if not isinstance(expected, list) or not expected:
        raise ValueError("incubator preserve_magics must list existing chart magics")
    active_profile = target.get("active_profile")
    if not isinstance(active_profile, str) or not active_profile:
        raise ValueError("incubator active_profile is required")
    observed = scan_incubator_charts(Path(str(target["data_root"])), active_profile)
    for magic in expected:
        paths = observed.get(int(magic), [])
        if len(paths) != 1:
            raise ValueError(f"existing incubator magic {magic} is missing or ambiguous")
    return observed


def load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("targets"), dict):
        raise TypeError("invalid pipeline agent configuration")
    targets = payload["targets"]
    if any(name in targets for name in _REAL_ROLES):
        for name in _REAL_ROLES:
            if name in targets and targets[name].get("mode") != "read_only":
                raise ValueError(f"real target {name} must remain read_only")
    if not _EXECUTABLE_ROLES.issubset(targets):
        raise ValueError("tester and incubator demo targets are required")
    return payload


def request_json(url: str, method: str, key: str, payload: dict[str, Any] | None = None) -> Any:
    data = json.dumps(payload).encode() if payload is not None else None
    request = Request(url, data=data, method=method, headers={"X-Pipeline-Agent-Key": key, "Content-Type": "application/json"})
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode())


def validate_command(command: dict[str, Any], config: dict[str, Any]) -> None:
    payload = command.get("payload") or {}
    role = payload.get("target_group")
    if role not in _EXECUTABLE_ROLES or role not in config["targets"]:
        raise ValueError("command target is not executable by this agent")
    if command["command_type"] == "MT5_TESTER" and role != "SQX_VS_MT5_TESTER":
        raise ValueError("tester command has invalid target")
    if command["command_type"] == "DEMO_INSTALL" and role != "CONTABO_INCUBATOR_DEMO":
        raise ValueError("demo installation has invalid target")
    if command["command_type"] in {"FORJA_GENERATE", "SQX_START", "SQX_STOP"} and role != "ANALYSIS":
        raise ValueError("analysis command has invalid target")


def _inside_roots(path: Path, roots: list[str]) -> Path:
    resolved = path.resolve()
    if not any(resolved.is_relative_to(Path(root).resolve()) for root in roots):
        raise ValueError("path is outside allowed source roots")
    return resolved


def sealed_demo_plan(payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Require the exact chart contract before any MT5-side mutation."""
    plan = payload.get("demo_plan")
    declared = payload.get("demo_plan_sha256")
    if not isinstance(plan, dict) or not isinstance(declared, str):
        raise ValueError("sealed demo plan and sha256 are required")
    canonical = json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()
    actual = hashlib.sha256(canonical).hexdigest()
    if actual != declared:
        raise ValueError("sealed demo plan hash mismatch")
    required = ("source_mq5", "symbol", "timeframe", "expert_relative_path", "magic_number", "profile_name")
    if any(not plan.get(field) for field in required):
        raise ValueError("sealed demo plan is incomplete")
    return plan, actual


def execute(command: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Execute only the two allowed MT5 operations in the Contabo desktop session."""
    validate_command(command, config)
    payload = command["payload"]
    role = payload["target_group"]
    target = config["targets"][role]
    if command["command_type"] == "FORJA_GENERATE":
        required = ("entry_id", "base", "capa", "direccion")
        if any(not isinstance(payload.get(field), str) for field in required):
            raise ValueError("FORJA generation requires catalog entry, base, layer and direction")
        command_line = [
            str(target["python"]), str(target["forja_cli"]), "catalogo", "generar",
            str(payload["entry_id"]), "--base", str(payload["base"]), "--capa",
            str(payload["capa"]), "--direccion", str(payload["direccion"]),
        ]
        if isinstance(payload.get("nombre"), str) and payload["nombre"]:
            command_line.extend(["--nombre", str(payload["nombre"])])
        completed = subprocess.run(command_line, check=False, capture_output=True, text=True, timeout=120)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "FORJA generation failed")
        return {"generated": True, "output": completed.stdout.strip()}
    if command["command_type"] in {"SQX_START", "SQX_STOP"}:
        configured = target.get("sqx_start_command" if command["command_type"] == "SQX_START" else "sqx_stop_command")
        if not isinstance(configured, list) or not configured or not all(isinstance(part, str) for part in configured):
            raise ValueError("SQX command is not configured")
        project = _inside_roots(Path(str(payload["project_path"])), config["allowed_source_roots"])
        completed = subprocess.run([part.replace("{project}", str(project)) for part in configured], check=False, capture_output=True, text=True, timeout=120)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "SQX command failed")
        return {"project": str(project), "status": "requested", "output": completed.stdout.strip()}
    if command["command_type"] == "MT5_TESTER":
        sqx = _inside_roots(Path(str(payload["sqx_path"])), config["allowed_source_roots"])
        mq5 = _inside_roots(Path(str(payload["mql5_path"])), config["allowed_source_roots"])
        configured = target.get("backtest_command")
        if not isinstance(configured, list) or not configured or not all(isinstance(part, str) for part in configured):
            raise ValueError("tester backtest command is not configured")
        command_line = [part.replace("{sqx}", str(sqx)).replace("{mq5}", str(mq5)) for part in configured]
        completed = subprocess.run(command_line, check=False, capture_output=True, text=True, timeout=14400)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "MT5 tester runner returned an error")
        manifest_match = _MANIFEST_PATTERN.search(completed.stdout)
        recorder = target.get("record_backtest_command")
        if manifest_match is None or not isinstance(recorder, list) or not recorder:
            raise RuntimeError("tester completed without configured sealed manifest recorder")
        manifest = _inside_roots(Path(manifest_match.group(1).strip()), config["allowed_source_roots"])
        recorded = subprocess.run(
            [str(part).replace("{manifest}", str(manifest)) for part in recorder],
            check=False, capture_output=True, text=True, timeout=120,
        )
        if recorded.returncode != 0:
            raise RuntimeError(recorded.stderr.strip() or "sealed manifest registration failed")
        return {"sqx_sha256": hashlib.sha256(sqx.read_bytes()).hexdigest(), "mql5_sha256": hashlib.sha256(mq5.read_bytes()).hexdigest(), "manifest": str(manifest), "registration": recorded.stdout.strip()}
    if command["command_type"] == "DEMO_INSTALL":
        observed = assert_existing_incubator_identity(target)
        plan, plan_sha256 = sealed_demo_plan(payload)
        payload = {**payload, **plan}
        attach_command = target.get("demo_attach_command")
        if not isinstance(attach_command, list) or not attach_command:
            raise ValueError("demo chart attachment command is not configured")
        plan_dir_value = target.get("demo_plan_dir")
        if not isinstance(plan_dir_value, str) or not plan_dir_value:
            raise ValueError("demo plan directory is not configured")
        plan_dir = Path(plan_dir_value)
        plan_dir.mkdir(parents=True, exist_ok=True)
        plan_path = plan_dir / f"{plan_sha256}.json"
        plan_path.write_text(json.dumps(plan, sort_keys=True, separators=(",", ":")), encoding="utf-8")
        new_magic = int(payload["magic_number"])
        if new_magic in observed:
            raise ValueError("demo magic is already attached to an existing chart")
        source = _inside_roots(Path(str(payload["source_mq5"])), config["allowed_source_roots"])
        relative = Path(str(payload["expert_relative_path"]))
        if source.suffix.casefold() != ".mq5" or relative.is_absolute() or ".." in relative.parts:
            raise ValueError("invalid demo expert path")
        destination = Path(target["data_root"]) / "MQL5" / "Experts" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
        editor = Path(str(target["metaeditor"]))
        before = destination.with_suffix(".ex5").stat().st_mtime_ns if destination.with_suffix(".ex5").exists() else None
        log = destination.with_suffix(".compile.log")
        subprocess.run([str(editor), f'/compile:"{destination}"', f'/log:"{log}"'], check=False, timeout=120)
        binary = destination.with_suffix(".ex5")
        if not binary.is_file() or binary.stat().st_mtime_ns == before:
            raise RuntimeError("MetaEditor did not produce an updated EX5")
        profile = str(payload["profile_name"])
        if not profile.startswith(str(config["allowed_profile_prefix"])):
            raise ValueError("demo profile does not use the isolated allowed prefix")
        completed = subprocess.run(
            [str(part).replace("{expert}", str(destination)).replace("{magic}", str(new_magic)).replace("{profile}", profile).replace("{plan_sha256}", plan_sha256).replace("{plan}", str(plan_path)) for part in attach_command],
            check=False, capture_output=True, text=True, timeout=120,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "demo chart attachment failed")
        after = assert_existing_incubator_identity(target)
        if len(after.get(new_magic, [])) != 1:
            raise RuntimeError("demo chart attachment did not produce one isolated chart")
        return {
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "ex5_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
            "compiled": True,
            "preserved_chart_magics": sorted(observed),
            "attached_magic": new_magic,
            "profile_name": profile,
            "demo_plan_sha256": plan_sha256,
        }
    raise ValueError("command handler is not installed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    api_key = os.environ.get("PIPELINE_AGENT_API_KEY")
    if not api_key:
        raise SystemExit("PIPELINE_AGENT_API_KEY is required")
    commands = request_json(f"{config['core_url']}/api/v1/pipeline-orchestrator/agent/commands", "GET", api_key)
    for command in commands:
        try:
            result = {"status": "SUCCEEDED", "result": execute(command, config)}
        except (KeyError, OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
            result = {"status": "FAILED", "result": {"reason": str(exc)}}
        request_json(f"{config['core_url']}/api/v1/pipeline-orchestrator/agent/commands/{command['id']}/result", "POST", api_key, result)
    if not args.once:
        raise SystemExit("run under a service wrapper that invokes --once on the configured interval")


if __name__ == "__main__":
    main()
