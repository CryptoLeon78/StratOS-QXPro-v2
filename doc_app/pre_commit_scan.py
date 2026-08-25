"""Guardian PreToolUse para Claude Code — StratOS-QXPro.

Se registra en .claude/settings.json como hook PreToolUse sobre Bash.
Recibe el payload del hook por stdin (JSON con tool_input.command).
Solo actua cuando el comando es un `git commit`: escanea los archivos
staged en busca de violaciones de la regla P11 (cero hardcoding).

Codigos de salida (contrato de hooks de Claude Code):
  0 -> permitir. 2 -> bloquear (stderr se devuelve al agente).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ALLOWED_PATH_PARTS = {
    "tests", "test", "seed", "scripts", "migrations", "alembic", "node_modules",
    "design_tokens.json", "ui_strings.es.json", "thresholds.seed.json",
    "dist", "build", ".venv", "__pycache__", "docs",
}
CODE_EXTENSIONS = {".py", ".ts", ".tsx", ".css", ".scss"}
HEX_COLOR = re.compile(r"#[0-9a-fA-F]{3,8}\b")
MAGIC_NUMBER = re.compile(r"(?<![\w.])(\d+\.\d+|\d{2,})(?![\w.%])")
ALLOWED_NUMBERS = {"10", "100", "1000", "60", "24", "3600", "86400", "252"}


def staged_files() -> list[Path]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return []
    return [Path(line.strip()) for line in result.stdout.splitlines() if line.strip()]


def scan_file(path: Path) -> list[str]:
    if path.suffix not in CODE_EXTENSIONS:
        return []
    if any(part in ALLOWED_PATH_PARTS for part in path.parts):
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []
    findings: list[str] = []
    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith(("#", "//", "*")) or "ASSUMPTION" in line:
            continue
        for m in HEX_COLOR.finditer(line):
            findings.append(f"{path}:{lineno} color hex {m.group(0)} -> design_tokens.json")
        if path.suffix in {".py", ".ts", ".tsx"} and ("=" in line or "if " in line or "return" in line):
            if re.search(r"(port|version|year|20\d\d|http)", line, re.I):
                continue
            for m in MAGIC_NUMBER.finditer(line):
                value = m.group(1)
                if value in ALLOWED_NUMBERS:
                    continue
                findings.append(f"{path}:{lineno} literal numerico {value} -> SystemConfig/Settings")
    return findings


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    if "git commit" not in command:
        return 0

    findings: list[str] = []
    for path in staged_files():
        findings.extend(scan_file(path))

    if not findings:
        return 0

    report = "\n".join(findings[:30])
    sys.stderr.write(
        "[P11 cero-hardcoding] Commit bloqueado. Mueve cada literal a su fuente "
        "(SystemConfig / Settings / design_tokens.json / ui_strings.es.json) o "
        "justificalo en ASSUMPTIONS.md:\n" + report + "\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
