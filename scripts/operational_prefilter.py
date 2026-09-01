"""Construye una cola pequeña, reproducible y evidenciada antes de SQX_vs_MT5.

No sustituye WFE, Monte Carlo ni la revisión de costes: éstos deben llegar como
artefactos sellados desde SQX/FORJA. Sin ellos un candidato sigue siendo
``STATIC_VALIDATED`` en inventario y queda fuera de la cola MT5, sin inventar
una transición de pipeline ni un resultado de robustez.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

VERDICT_PATTERN = re.compile(r"VEREDICTO:\s*(VALIDADA|TOLERABLE|DISCREPANTE)")
REQUIRED_THRESHOLD_KEYS = (
    "pipeline_min_trades",
    "pipeline_min_days",
    "pipeline_pf",
    "pipeline_exp",
    "pipeline_sharpe",
    "pipeline_maxdd",
    "pipeline_min_freq_week",
    "wfe_min",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seal_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON objeto requerido: {path}")
    return data


def load_thresholds(path: Path) -> dict[str, float]:
    data = load_object(path)
    missing = [
        key for key in REQUIRED_THRESHOLD_KEYS if not isinstance(data.get(key), (int, float))
    ]
    if missing:
        raise ValueError(f"thresholds sin claves requeridas: {', '.join(missing)}")
    return {key: float(data[key]) for key in REQUIRED_THRESHOLD_KEYS}


def _normalise_caps(data: dict[str, Any]) -> None:
    """Separa el tope de validación del de admisión, aceptando el formato v2.

    Hasta la v2 un único `max_per_symbol_timeframe` gobernaba la cola al Strategy
    Tester, mezclando dos decisiones que no son la misma: cuántas estrategias se
    *validan* (un presupuesto de CPU) y cuántas pueden *convivir* en Incubadora (una
    restricción de riesgo de portfolio). El efecto medido fue que 215 de 217 candidatas
    quedaban en `HOLD_DIVERSITY_CAP` por ser todas `AUDCAD/H4`, sin que nadie las
    estuviera admitiendo a ninguna parte.

    Una política v2 se lee como antes -- su tope se aplica a la validación y se
    reutiliza como tope de admisión -- para que una configuración existente no cambie
    de comportamiento en silencio.
    """
    if "validation_queue" not in data:
        legacy_bucket_cap = data.get("max_per_symbol_timeframe")
        data["validation_queue"] = {
            "max_queue": data.get("max_mt5_queue"),
            "max_per_symbol_timeframe": legacy_bucket_cap,
        }
        data.setdefault(
            "incubator_admission",
            {"max_per_symbol_timeframe": legacy_bucket_cap, "max_concurrent": None},
        )


def _require_positive_int_or_none(value: Any, name: str) -> None:
    if value is None:
        return
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} debe ser entero positivo o null")


def load_policy(path: Path) -> dict[str, Any]:
    data = load_object(path)
    required = (
        "version",
        "wfe_f2_gate",
        "require_monte_carlo_evidence",
        "require_cost_evidence",
    )
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"política incompleta: {', '.join(missing)}")
    _normalise_caps(data)

    queue_policy = data["validation_queue"]
    if not isinstance(queue_policy, dict):
        raise ValueError("validation_queue debe ser un objeto")
    if not isinstance(queue_policy.get("max_queue"), int) or queue_policy["max_queue"] < 1:
        raise ValueError("validation_queue.max_queue debe ser entero positivo")
    _require_positive_int_or_none(
        queue_policy.get("max_per_symbol_timeframe"),
        "validation_queue.max_per_symbol_timeframe",
    )

    admission = data.get("incubator_admission")
    if not isinstance(admission, dict):
        raise ValueError("incubator_admission debe ser un objeto")
    _require_positive_int_or_none(
        admission.get("max_per_symbol_timeframe"),
        "incubator_admission.max_per_symbol_timeframe",
    )
    _require_positive_int_or_none(
        admission.get("max_concurrent"), "incubator_admission.max_concurrent"
    )
    f2_gate = data["wfe_f2_gate"]
    if not isinstance(f2_gate, dict) or not isinstance(f2_gate.get("enabled"), bool):
        raise ValueError("wfe_f2_gate.enabled debe ser booleano")
    statuses = f2_gate.get("accepted_statuses")
    if not isinstance(statuses, list) or not statuses or not all(
        isinstance(value, str) and value for value in statuses
    ):
        raise ValueError("wfe_f2_gate.accepted_statuses debe ser lista no vacía de estados")
    return data


def load_quality_evidence(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    data = load_object(path)
    entries = data.get("items")
    if not isinstance(entries, list):
        raise ValueError("quality evidence requiere una lista items")
    out: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("sqx_sha256"), str):
            raise ValueError("quality evidence contiene un item sin sqx_sha256")
        key = entry["sqx_sha256"]
        if key in out:
            raise ValueError(f"quality evidence duplicada para SHA: {key}")
        out[key] = entry
    return out


def completed_tested_hashes(root: Path | None) -> dict[str, dict[str, str]]:
    """Lee manifests terminados para impedir que un SHA vuelva a entrar a la cola.

    No confía en nombres ni altera base de datos: sólo necesita returncode cero
    y el veredicto contenido en el stdout sellado por el runner.
    """
    if root is None or not root.is_dir():
        return {}
    completed: dict[str, dict[str, str]] = {}
    for manifest_path in sorted(root.rglob("run-manifest.json")):
        try:
            manifest = load_object(manifest_path)
            result = manifest.get("result") or {}
            match = VERDICT_PATTERN.search(str(result.get("stdout", "")))
            source = manifest.get("source") or {}
            sqx_sha = source.get("sqx_sha256")
            if result.get("returncode") == 0 and match and isinstance(sqx_sha, str):
                completed[sqx_sha] = {
                    "run_id": str(manifest.get("run_id", "unknown")),
                    "verdict": match.group(1),
                }
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    return completed


def sealed_artifact_reason(block: dict[str, Any], prefix: str) -> str | None:
    raw_path, claimed_hash = block.get("artifact_path"), block.get("sha256")
    artifact_path = Path(str(raw_path)) if raw_path else None
    if not artifact_path or not artifact_path.is_file() or not isinstance(claimed_hash, str):
        return f"{prefix}_ARTIFACT_MISSING"
    if sha256_file(artifact_path) != claimed_hash:
        return f"{prefix}_ARTIFACT_HASH_MISMATCH"
    return None


def evidence_reasons(
    evidence: dict[str, Any] | None, policy: dict[str, Any], thresholds: dict[str, float]
) -> list[str]:
    if evidence is None:
        required = []
        if policy["wfe_f2_gate"]["enabled"]:
            required.append("WFE")
        if policy["require_monte_carlo_evidence"]:
            required.append("MONTE_CARLO")
        if policy["require_cost_evidence"]:
            required.append("COSTS")
        return [f"MISSING_{value}_EVIDENCE" for value in required]

    reasons: list[str] = []
    if policy["wfe_f2_gate"]["enabled"]:
        wfe = evidence.get("wfe")
        if not isinstance(wfe, dict) or not isinstance(wfe.get("value"), (int, float)):
            reasons.append("MISSING_WFE_EVIDENCE")
        elif wfe.get("f2_gate_status") not in policy["wfe_f2_gate"]["accepted_statuses"]:
            reasons.append("WFE_F2_EVIDENCE_NOT_VALIDATED")
        else:
            artifact_reason = sealed_artifact_reason(wfe, "WFE")
            if artifact_reason:
                reasons.append(artifact_reason)
            if float(wfe["value"]) < thresholds["wfe_min"]:
                reasons.append("WFE_BELOW_CONTRACT")
    if policy["require_monte_carlo_evidence"]:
        monte_carlo = evidence.get("monte_carlo")
        if not isinstance(monte_carlo, dict) or monte_carlo.get("p95_no_ruin") is not True:
            reasons.append("MONTE_CARLO_P95_NOT_VERIFIED")
        else:
            artifact_reason = sealed_artifact_reason(monte_carlo, "MONTE_CARLO")
            if artifact_reason:
                reasons.append(artifact_reason)
    if policy["require_cost_evidence"]:
        costs = evidence.get("costs")
        if not isinstance(costs, dict) or costs.get("session_aware") is not True:
            reasons.append("COSTS_NOT_SESSION_AWARE")
        else:
            artifact_reason = sealed_artifact_reason(costs, "COSTS")
            if artifact_reason:
                reasons.append(artifact_reason)
    return reasons


def baseline_metrics(sqx_path: Path) -> dict[str, Any]:
    from core.services.sqx_baseline_parser import parse_sqx144_baseline

    parsed = parse_sqx144_baseline(sqx_path.read_bytes())
    try:
        start = datetime.fromisoformat(parsed.backtest_from).date()
        end = datetime.fromisoformat(parsed.backtest_to).date()
    except ValueError as exc:
        raise ValueError("fechas SQX inválidas") from exc
    history_days = max((end - start).days, 0)
    trades_per_week = parsed.trade_count / (history_days / 7) if history_days else 0.0
    return {
        "profit_factor": parsed.profit_factor,
        "expectancy_r": parsed.expectancy_r,
        "sharpe": parsed.sharpe,
        "max_dd_pct": parsed.max_dd_pct,
        "trade_count": parsed.trade_count,
        "history_days": history_days,
        "trades_per_week": trades_per_week,
        "backtest_from": parsed.backtest_from,
        "backtest_to": parsed.backtest_to,
        "symbol": parsed.symbol,
        "timeframe": parsed.timeframe,
    }


def baseline_reasons(metrics: dict[str, Any], thresholds: dict[str, float]) -> list[str]:
    checks = (
        ("trade_count", "pipeline_min_trades", "TRADE_COUNT_BELOW_CONTRACT", lambda x, y: x < y),
        ("history_days", "pipeline_min_days", "HISTORY_DAYS_BELOW_CONTRACT", lambda x, y: x < y),
        ("profit_factor", "pipeline_pf", "PF_BELOW_CONTRACT", lambda x, y: x < y),
        ("expectancy_r", "pipeline_exp", "EXPECTANCY_BELOW_CONTRACT", lambda x, y: x < y),
        ("sharpe", "pipeline_sharpe", "SHARPE_BELOW_CONTRACT", lambda x, y: x < y),
        ("max_dd_pct", "pipeline_maxdd", "MAX_DD_ABOVE_CONTRACT", lambda x, y: x > y),
    )
    return [
        reason
        for metric, threshold, reason, fails in checks
        if fails(metrics[metric], thresholds[threshold])
    ]


def baseline_warnings(metrics: dict[str, Any], thresholds: dict[str, float]) -> list[str]:
    """Separa frecuencia baja de los rechazos duros.

    El propio contrato permite el mínimo absoluto de treinta trades aunque la
    frecuencia sea menor de dos por semana, indicando menor fiabilidad. Por
    eso nunca se maquilla como aprobado, pero tampoco se descarta un candidato
    sólo por ser poco frecuente: exige evidencia de robustez más completa.
    """
    if metrics["trades_per_week"] < thresholds["pipeline_min_freq_week"]:
        return ["FREQUENCY_BELOW_CONTRACT_REVIEW"]
    return []


def evaluate_items(
    items: list[dict[str, Any]],
    *,
    policy: dict[str, Any],
    thresholds: dict[str, float],
    quality_evidence: dict[str, dict[str, Any]],
    completed: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    for item in items:
        decision: dict[str, Any] = {
            "strategy_name": item.get("strategy_name"),
            "sqx_sha256": item.get("sqx_sha256"),
            "mql5_sha256": item.get("mql5_sha256"),
            "sqx_path": item.get("sqx_path"),
            "mql5_path": item.get("mql5_path"),
            "symbol": item.get("symbol"),
            "timeframe": item.get("timeframe"),
            "inventory_status": item.get("status"),
            "decision": "HOLD",
            "reasons": [],
            "warnings": [],
        }
        if item.get("status") != "STATIC_VALIDATED" or not isinstance(item.get("sqx_path"), str):
            decision["reasons"] = ["INVENTORY_NOT_STATIC_VALIDATED"]
            decisions.append(decision)
            continue
        sqx_path = Path(item["sqx_path"])
        if not sqx_path.is_file() or sha256_file(sqx_path) != item.get("sqx_sha256"):
            decision["reasons"] = ["SQX_SOURCE_HASH_MISMATCH_OR_MISSING"]
            decisions.append(decision)
            continue
        try:
            metrics = baseline_metrics(sqx_path)
        except ValueError as exc:
            decision["reasons"] = [f"SQX_BASELINE_PARSE_FAILED:{exc}"]
            decisions.append(decision)
            continue
        decision["metrics"] = metrics
        decision["warnings"] = baseline_warnings(metrics, thresholds)
        baseline_failures = baseline_reasons(metrics, thresholds)
        if baseline_failures:
            decision["reasons"] = baseline_failures
            decisions.append(decision)
            continue
        sqx_sha = str(item["sqx_sha256"])
        if sqx_sha in completed:
            decision["decision"] = "EXCLUDED_ALREADY_TESTED"
            decision["completed_test"] = completed[sqx_sha]
            decisions.append(decision)
            continue
        quality_failures = evidence_reasons(quality_evidence.get(sqx_sha), policy, thresholds)
        if quality_failures:
            decision["reasons"] = quality_failures
            decisions.append(decision)
            continue
        decision["decision"] = "ELIGIBLE"
        decisions.append(decision)
    return decisions


def select_queue(decisions: list[dict[str, Any]], policy: dict[str, Any]) -> list[dict[str, Any]]:
    eligible = [item for item in decisions if item["decision"] == "ELIGIBLE"]
    # Sólo métricas declaradas por el parser; orden estable por hash para desempates.
    eligible.sort(
        key=lambda item: (
            -float(item["metrics"]["profit_factor"]),
            -float(item["metrics"]["sharpe"]),
            -float(item["metrics"]["expectancy_r"]),
            float(item["metrics"]["max_dd_pct"]),
            str(item["sqx_sha256"]),
        )
    )
    # Una política v2 (topes planos) puede llegar aquí sin pasar por load_policy; la
    # normalización es idempotente y evita que el formato antiguo reviente la cola.
    _normalise_caps(policy)
    queue_policy = policy["validation_queue"]
    validation_bucket_cap = queue_policy.get("max_per_symbol_timeframe")
    admission_bucket_cap = policy["incubator_admission"].get("max_per_symbol_timeframe")

    per_bucket: dict[tuple[str, str], int] = {}
    queue: list[dict[str, Any]] = []
    for item in eligible:
        bucket = (str(item.get("symbol")), str(item.get("timeframe")))
        rank_en_bucket = per_bucket.get(bucket, 0) + 1
        if validation_bucket_cap is not None and rank_en_bucket > validation_bucket_cap:
            item["decision"] = "HOLD_DIVERSITY_CAP"
            item["reasons"] = ["SYMBOL_TIMEFRAME_CAP"]
            continue
        if len(queue) >= queue_policy["max_queue"]:
            item["decision"] = "HOLD_QUEUE_CAP"
            item["reasons"] = ["MT5_QUEUE_CAP"]
            continue
        per_bucket[bucket] = rank_en_bucket
        item["queue_rank"] = len(queue) + 1
        # Concentración anotada, no aplicada: validar no admite a ninguna parte. Cuando
        # exista admisión a Incubadora, el tope de portfolio se aplica allí y esta marca
        # dice cuántas del mismo bucket llegarían por delante.
        item["admission_bucket_rank"] = rank_en_bucket
        item["exceeds_incubator_admission_cap"] = (
            admission_bucket_cap is not None and rank_en_bucket > admission_bucket_cap
        )
        queue.append(item)
    return queue


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--thresholds", type=Path, default=Path("config/thresholds.seed.json"))
    parser.add_argument("--policy", type=Path, default=Path("config/operational_prefilter.json"))
    parser.add_argument("--quality-evidence", type=Path)
    parser.add_argument("--completed-backtests", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    inventory = load_object(args.inventory)
    items = inventory.get("items")
    if not isinstance(items, list):
        raise SystemExit("inventory requiere lista items")
    thresholds, policy = load_thresholds(args.thresholds), load_policy(args.policy)
    evidence = load_quality_evidence(args.quality_evidence)
    decisions = evaluate_items(
        items,
        policy=policy,
        thresholds=thresholds,
        quality_evidence=evidence,
        completed=completed_tested_hashes(args.completed_backtests),
    )
    queue = select_queue(decisions, policy)
    payload = {
        "version": policy["version"],
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "inventory": {"path": str(args.inventory.resolve()), "sha256": sha256_file(args.inventory)},
        "thresholds": {
            "path": str(args.thresholds.resolve()),
            "sha256": sha256_file(args.thresholds),
        },
        "policy": {"path": str(args.policy.resolve()), "sha256": sha256_file(args.policy)},
        "quality_evidence": (
            {
                "path": str(args.quality_evidence.resolve()),
                "sha256": sha256_file(args.quality_evidence),
            }
            if args.quality_evidence
            else None
        ),
        "summary": {
            "inventory_items": len(items),
            "eligible_before_diversity": sum(item["decision"] == "ELIGIBLE" for item in decisions),
            "mt5_queue": len(queue),
            "hold": sum(item["decision"].startswith("HOLD") for item in decisions),
            "already_tested": sum(
                item["decision"] == "EXCLUDED_ALREADY_TESTED" for item in decisions
            ),
        },
        "queue": queue,
        "decisions": decisions,
    }
    payload["manifest_sha256"] = seal_payload(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    eligible_count = payload["summary"]["eligible_before_diversity"]
    print(f"prefilter queue={len(queue)} eligible={eligible_count} output={args.output}")


if __name__ == "__main__":
    main()
