"""StratOS-QXPro MCP server — fuente consultable del proyecto para Claude Code.

Instalacion: se registra en .mcp.json (raiz del repo) y se ejecuta con:
    python mcp/stratos_mcp_server.py

Requisitos: pip install mcp  (SDK oficial, FastMCP)

Expone como tools la verdad contractual del proyecto: umbrales, tokens de
diseno, specs de pestanas, firmas de formulas, criterios de aceptacion,
escenarios de seed y el escaner anti-hardcoding (regla P11).
Si el codigo y este servidor discrepan, manda este servidor (o se actualiza
el threshold via PR documentado).
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from mcp.server.fastmcp import FastMCP

ROOT = Path(os.environ.get("STRATOS_ROOT", Path(__file__).resolve().parent.parent))
DOC_APP = ROOT / "doc_app"
CONFIG = ROOT / "config"
PROMPT = DOC_APP / "PROMPT_MAESTRO.md"
TOKENS = DOC_APP / "design_tokens.json"
THRESHOLDS = CONFIG / "thresholds.seed.json"

mcp = FastMCP("stratos")


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {"error": f"no existe {path}; completar en la fase que lo crea (ver PROMPT_MAESTRO PARTE 12)"}
    return json.loads(path.read_text(encoding="utf-8"))


def _prompt_section(part: str) -> str:
    if not PROMPT.exists():
        return f"no existe {PROMPT}"
    text = PROMPT.read_text(encoding="utf-8")
    pattern = re.compile(rf"^## PARTE {re.escape(part)}\b.*?(?=^## PARTE |\Z)", re.S | re.M)
    match = pattern.search(text)
    return match.group(0).strip() if match else f"PARTE {part} no encontrada en el prompt maestro"


@mcp.tool()
def get_thresholds() -> dict:
    """Devuelve TODOS los umbrales contractuales (SystemConfig defaults):
    semaforo, kill-switch, pipeline (7 gates), sizing, correlaciones, Monte Carlo,
    watchdog, auditoria, UMS, challenger. Usar SIEMPRE antes de escribir logica
    con numeros: prohibido hardcodear umbrales (regla P11)."""
    return _read_json(THRESHOLDS)


@mcp.tool()
def get_design_tokens() -> dict:
    """Devuelve los tokens de diseno contractuales (colores, tipografia, radios,
    espaciados, escala del heatmap). El tema de Tailwind se GENERA desde aqui;
    ningun color o espaciado suelto en componentes."""
    return _read_json(TOKENS)


@mcp.tool()
def get_module_spec(tab: str) -> str:
    """Spec funcional + visual de una pestaña. tab: resumen | cuentas-ea | pipeline |
    bots | portfolio | salud | riesgo | ejecucion | escalado | graveyard | auditoria.
    Devuelve la seccion correspondiente de la PARTE 7 del prompt maestro."""
    index = {
        "resumen": "7.1", "cuentas-ea": "7.2", "pipeline": "7.3", "bots": "7.4",
        "portfolio": "7.5", "salud": "7.6", "riesgo": "7.7", "ejecucion": "7.8",
        "escalado": "7.9", "graveyard": "7.10", "auditoria": "7.11",
    }
    section = index.get(tab.lower())
    if not section:
        return f"pestaña desconocida '{tab}'. Validas: {', '.join(index)}"
    part7 = _prompt_section("7")
    pattern = re.compile(rf"^### {re.escape(section)}\..*?(?=^### 7\.\d+|\Z)", re.S | re.M)
    match = pattern.search(part7)
    return match.group(0).strip() if match else f"seccion {section} no encontrada"


@mcp.tool()
def get_formula_signature(name: str) -> str:
    """Firma contractual + semantica + tests obligatorios de una formula
    (r_multiple, expectancy_r, rolling_profit_factor, correlation_matrix,
    historical_var, historical_cvar, monte_carlo_maxdd, ols_alpha_beta,
    watchdog_deviation, audit_discrepancy, max_drawdown_pct, loss_streak,
    streak_p99_threshold, walk_forward_efficiency, page_hinkley, trades_per_week,
    decision_eta_days, counterfactual_impulse, sustainable_withdrawal)."""
    part8 = _prompt_section("8")
    for line_block in re.findall(rf"def {re.escape(name)}\(.*?(?=\ndef |\Z)", part8, re.S):
        return line_block.strip()
    return f"formula '{name}' no encontrada en PARTE 8"


@mcp.tool()
def get_acceptance_criteria() -> str:
    """Los 17 criterios de aceptacion globales (PARTE 15) que deben quedar
    automatizados y verdes en la fase G8."""
    return _prompt_section("15")


@mcp.tool()
def get_seed_scenario(name: str) -> str:
    """Escenarios contractuales del seed: full | small_scale | crash_21 |
    degraded_bot | orphan_trades | audit_error | impulses | cemetery | news.
    Devuelve el extracto relevante de la PARTE 13."""
    part13 = _prompt_section("13")
    keywords = {
        "crash_21": "crash_21", "degraded_bot": "NARANJA 12 días",
        "orphan_trades": "huérfanos", "audit_error": "inject-audit-error",
        "impulses": "impulsos", "cemetery": "Graveyard", "news": "noticias",
        "full": "Producción", "small_scale": "small_scale",
    }
    key = keywords.get(name.lower())
    if not key:
        return f"escenario desconocido '{name}'. Validos: {', '.join(keywords)}"
    lines = [ln for ln in part13.splitlines() if key.lower() in ln.lower()]
    return "\n".join(lines) if lines else f"sin menciones de '{key}' en PARTE 13"


# --- escaner anti-hardcoding (regla P11) --------------------------------------

ALLOWED_PATH_PARTS = {
    "tests", "test", "seed", "migrations", "alembic", "node_modules",
    "design_tokens.json", "ui_strings.es.json", "thresholds.seed.json",
    ".env", "dist", "build", ".venv", "__pycache__",
}
CODE_EXTENSIONS = {".py", ".ts", ".tsx", ".css", ".scss"}
HEX_COLOR = re.compile(r"#[0-9a-fA-F]{3,8}\b")
MAGIC_NUMBER = re.compile(r"(?<![\w.])(\d+\.\d+|\d{2,})(?![\w.%])")
ALLOWED_NUMBERS = {"10", "100", "1000", "60", "24", "3600", "86400", "252"}


@mcp.tool()
def scan_hardcoding(path: str = ".") -> dict:
    """Escanea codigo en busca de violaciones de la regla CERO-HARDCODING (P11):
    colores hex fuera de design_tokens.json y literales numericos sospechosos
    (umbrales, porcentajes) en archivos de logica. Ejecutar antes de cada commit
    de fase; todo hallazgo se corrige o se justifica en ASSUMPTIONS.md."""
    target = (ROOT / path).resolve()
    findings: list[dict] = []
    for file in target.rglob("*"):
        if not file.is_file() or file.suffix not in CODE_EXTENSIONS:
            continue
        if any(part in ALLOWED_PATH_PARTS for part in file.parts):
            continue
        try:
            lines = file.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for lineno, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith(("#", "//", "*", "\"\"\"")) or "ASSUMPTION" in line:
                continue
            for m in HEX_COLOR.finditer(line):
                findings.append({"file": str(file.relative_to(ROOT)), "line": lineno,
                                 "kind": "hex_color", "value": m.group(0)})
            if file.suffix in {".py", ".ts", ".tsx"} and ("=" in line or "if " in line or "return" in line):
                for m in MAGIC_NUMBER.finditer(line):
                    value = m.group(1)
                    if value in ALLOWED_NUMBERS or value.startswith("0.") and float(value) == 0.0:
                        continue
                    if re.search(r"(port|version|year|20\d\d)", line, re.I):
                        continue
                    findings.append({"file": str(file.relative_to(ROOT)), "line": lineno,
                                     "kind": "numeric_literal", "value": value})
    return {"scanned": str(target), "findings": findings[:200], "total": len(findings),
            "policy": "P11: umbrales->SystemConfig, colores->design_tokens.json, textos->ui_strings.es.json"}


@mcp.tool()
def get_project_status() -> dict:
    """Resumen de que piezas de gobierno existen ya en el repo (util en G0 y
    para diagnosticar instalaciones incompletas)."""
    checks = {
        "prompt_maestro": PROMPT.exists(),
        "design_tokens": TOKENS.exists(),
        "thresholds_seed": THRESHOLDS.exists(),
        "claude_md": (ROOT / "CLAUDE.md").exists(),
        "skill": (ROOT / ".claude" / "skills" / "stratos-guardian" / "SKILL.md").exists(),
        "assumptions": (ROOT / "ASSUMPTIONS.md").exists(),
        "core_engine": (ROOT / "core-engine").exists(),
        "frontend": (ROOT / "frontend").exists(),
        "connector": (ROOT / "mt5-connector").exists(),
    }
    return {"root": str(ROOT), "checks": checks}


if __name__ == "__main__":
    mcp.run()
