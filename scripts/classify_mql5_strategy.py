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
_INDICATOR_DEFINE = re.compile(
    r"^#define\s+(?P<name>[A-Z0-9_]+).*?(?P<indicator>Sq[A-Za-z0-9]+)", re.MULTILINE
)
_STRUCTURAL_SIGNALS: dict[str, tuple[re.Pattern[str], ...]] = {
    # A low-tail condition followed by a recovery/cross is the executable shape
    # exported by SQX for the SPA35 daily-reversion candidates.  It is evidence
    # from the rule itself, never from a file name or strategy label.
    "MEAN_REVERSION": (
        re.compile(r"\bsqIsLowerPercentile\s*\(", re.IGNORECASE),
        re.compile(r"\bsqIsGreaterPercentile\s*\([^)]*(?:SqRSI|SqStochastic|SqCCI)", re.IGNORECASE),
        re.compile(
            r"\bindyCrosses(?:Above|Below)\s*\([^\n]*(?:sqOpen[^\n]*sqLow|sqLow[^\n]*sqOpen)",
            re.IGNORECASE,
        ),
    ),
    # A high-tail filter on a regression/price series is a directional momentum
    # condition.  Oscillator high-tail conditions remain mean-reversion above.
    "MOMENTUM": (
        re.compile(r"\bsqIsGreaterPercentile\s*\(", re.IGNORECASE),
        re.compile(
            r"\bsqIsGreaterPercentile(?=[\s\S]{0,500}\b(?:LINEARREGRESSION|SqMACD|sqROC|SqMomentum)(?:\b|_))",
            re.IGNORECASE,
        ),
        re.compile(r"\b(?:AWESOMEOSCILLATOR|SqAwesomeOscillator)(?:\b|_)", re.IGNORECASE),
    ),
    # Higher-timeframe close/open comparisons describe directional continuation.
    "TREND": (
        re.compile(r"\bsq(?:Monthly|Weekly)\s*\([^\n]*\b(?:Close|Open)\b", re.IGNORECASE),
        re.compile(r"\bsqGetIndicatorValue\s*\(\s*LOWEST(?:INRANGE)?_", re.IGNORECASE),
        re.compile(r"\bsqDaily\s*\([^\n]*\bHigh\b[^\n]*\bsqOpen\s*\(", re.IGNORECASE),
    ),
}


def classify_source(path: Path) -> dict[str, Any]:
    """Devuelve el perfil propuesto y la evidencia estática que lo sostiene."""
    source = path.read_text(encoding="utf-8", errors="strict")
    entry = _ENTRY_BLOCK.search(source)
    if entry is None:
        raise ValueError("no se encontró el bloque ejecutable de señales de entrada")
    rule = entry.group("body")
    indicator_definitions = {
        match.group("name"): match.group("indicator")
        for match in _INDICATOR_DEFINE.finditer(source)
    }
    resolved_indicators = [
        indicator
        for name, indicator in indicator_definitions.items()
        if re.search(rf"\b{re.escape(name)}\b", rule)
    ]
    direct_scores = {
        profile: sum(rule.count(signal) for signal in signals)
        + sum(indicator in signals for indicator in resolved_indicators)
        for profile, signals in _SIGNALS.items()
    }
    structural_evidence = {
        profile: [pattern.pattern for pattern in patterns if pattern.search(rule)]
        for profile, patterns in _STRUCTURAL_SIGNALS.items()
    }
    structural_scores = {profile: len(matches) for profile, matches in structural_evidence.items()}
    # A price-low recovery cross is more specific than an accompanying higher-
    # timeframe filter: it defines the trade trigger as a reversion entry.
    price_recovery_cross = _STRUCTURAL_SIGNALS["MEAN_REVERSION"][2].pattern
    if price_recovery_cross in structural_evidence["MEAN_REVERSION"]:
        structural_scores["MEAN_REVERSION"] += 1
    # The generic high-percentile primitive is momentum only with an explicitly
    # directional source.  This avoids mistaking an oscillator overbought signal
    # for a breakout.
    generic_high_percentile = _STRUCTURAL_SIGNALS["MOMENTUM"][0].pattern
    if (
        generic_high_percentile in structural_evidence["MOMENTUM"]
        and len(structural_evidence["MOMENTUM"]) < 2
    ):
        structural_scores["MOMENTUM"] = 0
        structural_evidence["MOMENTUM"] = []
    scores = {profile: direct_scores[profile] + structural_scores[profile] for profile in _SIGNALS}
    strongest = max(scores.values())
    leaders = [profile for profile, score in scores.items() if score == strongest and score > 0]
    proposed = leaders[0] if len(leaders) == 1 else "UNCLASSIFIED"
    return {
        "schema_version": "mql5-static-profile-classification-v2",
        "mql5_path": str(path.resolve()),
        "mql5_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "proposed_profile": proposed,
        "requires_operator_confirmation": proposed == "UNCLASSIFIED",
        "evidence": {
            "entry_rule_only": True,
            "signals_by_profile": scores,
            "direct_signals_by_profile": direct_scores,
            "structural_evidence_by_profile": structural_evidence,
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
    args.report.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"profile={payload['proposed_profile']} report={args.report}")


if __name__ == "__main__":
    main()
