"""Clasifica una fuente MQL5 exportada sin inferir el perfil por el nombre.

La salida es evidencia de revisión: no modifica inventario, bots ni MT5. Un
perfil sólo se propone cuando las reglas ejecutables aportan señales suficientes;
en cualquier otro caso devuelve ``UNCLASSIFIED`` para revisión humana.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


_SIGNALS: dict[str, tuple[str, ...]] = {
    "TREND": ("SqSuperTrend", "sqADXCrossover", "SqGannHiLo"),
    "MEAN_REVERSION": ("SqRSI", "SqLaguerreRSI", "SqStochastic", "SqCCI", "SqVWAPBollingerBands"),
    "MOMENTUM": ("SqMACD", "sqROC", "SqMomentum"),
}
_ENTRY_BLOCK = re.compile(r"// Rule: Trading signals(?P<body>.*?)// Rule: Long entry", re.DOTALL)
_INDICATOR_DEFINE = re.compile(r"^#define\s+(?P<name>[A-Z0-9_]+).*?(?P<indicator>Sq[A-Za-z0-9]+)", re.MULTILINE)


def classify_source(path: Path) -> dict[str, Any]:
    """Devuelve el perfil propuesto y la evidencia estática que lo sostiene."""
    source = path.read_text(encoding="utf-8", errors="strict")
    entry = _ENTRY_BLOCK.search(source)
    if entry is None:
        raise ValueError("no se encontró el bloque ejecutable de señales de entrada")
    rule = entry.group("body")
    indicator_definitions = {
        match.group("name"): match.group("indicator") for match in _INDICATOR_DEFINE.finditer(source)
    }
    resolved_indicators = [
        indicator for name, indicator in indicator_definitions.items() if re.search(rf"\b{re.escape(name)}\b", rule)
    ]
    scores = {
        profile: sum(rule.count(signal) for signal in signals)
        + sum(indicator in signals for indicator in resolved_indicators)
        for profile, signals in _SIGNALS.items()
    }
    strongest = max(scores.values())
    leaders = [profile for profile, score in scores.items() if score == strongest and score > 0]
    proposed = leaders[0] if len(leaders) == 1 else "UNCLASSIFIED"
    return {
        "schema_version": "mql5-static-profile-classification-v1",
        "mql5_path": str(path.resolve()),
        "mql5_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "proposed_profile": proposed,
        "requires_operator_confirmation": True,
        "evidence": {
            "entry_rule_only": True,
            "signals_by_profile": scores,
            "resolved_indicators": resolved_indicators,
            "entry_rule_sha256": hashlib.sha256(rule.encode("utf-8")).hexdigest(),
            "long_enabled": "LongEntrySignal =" in rule,
            "short_enabled": "ShortEntrySignal =" in rule,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mq5", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    payload = classify_source(args.mq5)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"profile={payload['proposed_profile']} report={args.report}")


if __name__ == "__main__":
    main()
