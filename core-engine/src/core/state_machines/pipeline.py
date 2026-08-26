"""PARTE 6.3: gate automatico de 7 criterios del pipeline F1-F7 (desde F4)."""

import json
from datetime import UTC, datetime
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.enums import ActorType, AlertLevel, Verdict
from core.db.models.decisions import Alert, DecisionLog
from core.db.models.pipeline import PipelineCandidate
from core.state_machines.hash_chain import GENESIS_HASH, compute_decision_hash
from core.state_machines.types import GateResult, PipelineGateConfig, PipelineGateMetrics


def _is_marginal(value: float, threshold: float, band: float) -> bool:
    return abs(value - threshold) / abs(threshold) < band


def evaluate_pipeline_gate(
    metrics: PipelineGateMetrics,
    config: PipelineGateConfig,
    sizing_cap_breach: bool = False,
) -> GateResult:
    """PARTE 6.3: los 7 criterios automaticos desde F4. Prioridad de
    veredicto: KILL (>=2 criterios fallan, o maxDD>=20%, o PF<1,1) > HOLD
    por SIZING_CAP (portfolio-wide, independiente de la calidad del propio
    candidato) > GO (7/7) > HOLD (1 criterio insuficiente/marginal)."""
    criteria = {
        "profit_factor": metrics.profit_factor > config.pf,
        "expectancy_r": metrics.expectancy_r > config.exp,
        "sharpe": metrics.sharpe > config.sharpe,
        "max_dd_pct": metrics.max_dd_pct < config.maxdd,
        "sample": metrics.oos_trades >= config.min_trades,
        "incubation": metrics.incubation_days >= config.min_days,
        "frequency": metrics.trades_per_week >= config.min_freq_week,
    }
    failing = [name for name, passed in criteria.items() if not passed]
    gates_passed = len(criteria) - len(failing)
    gates_total = len(criteria)
    provisional = metrics.oos_trades < config.min_trades

    if (
        len(failing) >= 2
        or metrics.max_dd_pct >= config.maxdd
        or metrics.profit_factor < config.kill_pf
    ):
        return GateResult(
            gates_passed=gates_passed,
            gates_total=gates_total,
            verdict=Verdict.KILL.value,
            verdict_reason=",".join(failing) if failing else "PF_BELOW_KILL_THRESHOLD",
            provisional=provisional,
        )

    if sizing_cap_breach:
        return GateResult(
            gates_passed=gates_passed,
            gates_total=gates_total,
            verdict=Verdict.HOLD.value,
            verdict_reason="SIZING_CAP",
            provisional=provisional,
        )

    if not failing:
        return GateResult(
            gates_passed=gates_passed,
            gates_total=gates_total,
            verdict=Verdict.GO.value,
            verdict_reason=None,
            provisional=False,
        )

    reason = "INSUFFICIENT_SAMPLE_OR_TIME" if failing[0] in {"sample", "incubation"} else None
    if reason is None:
        marginal_checks = {
            "profit_factor": (metrics.profit_factor, config.pf),
            "expectancy_r": (metrics.expectancy_r, config.exp),
            "sharpe": (metrics.sharpe, config.sharpe),
            "max_dd_pct": (metrics.max_dd_pct, config.maxdd),
            "frequency": (metrics.trades_per_week, config.min_freq_week),
        }
        value, threshold = marginal_checks[failing[0]]
        reason = (
            f"MARGINAL:{failing[0]}"
            if _is_marginal(value, threshold, config.marginal_band)
            else f"CRITERION_FAILED:{failing[0]}"
        )
    return GateResult(
        gates_passed=gates_passed,
        gates_total=gates_total,
        verdict=Verdict.HOLD.value,
        verdict_reason=reason,
        provisional=provisional,
    )


async def apply_pipeline_gate(
    session: AsyncSession,
    redis: Redis,
    candidate: PipelineCandidate,
    result: GateResult,
) -> None:
    """Actualiza PipelineCandidate con el veredicto, deja rastro en
    DecisionLog (toda evaluacion de gate, sea cual sea el veredicto) y
    publica en events:pipeline. KILL genera ademas un Alert CRITICA (abre
    el formulario de autopsia bloqueante en la UI, PARTE 6.3/7.3)."""
    now = datetime.now(UTC)
    candidate.gates_passed = result.gates_passed
    candidate.gates_total = result.gates_total
    candidate.verdict = Verdict(result.verdict)
    candidate.verdict_reason = result.verdict_reason
    candidate.provisional = result.provisional
    candidate.evaluated_at = now

    last_hash = (
        await session.execute(select(DecisionLog.hash).order_by(DecisionLog.id.desc()).limit(1))
    ).scalar_one_or_none()
    prev_hash = last_hash or GENESIS_HASH
    payload: dict[str, Any] = {
        "candidate_id": candidate.id,
        "bot_id": candidate.bot_id,
        "verdict": result.verdict,
        "verdict_reason": result.verdict_reason,
        "gates_passed": result.gates_passed,
        "gates_total": result.gates_total,
        "provisional": result.provisional,
    }
    new_hash = compute_decision_hash(
        prev_hash=prev_hash,
        ts=now,
        actor=ActorType.SYSTEM,
        module="pipeline",
        decision_type="PIPELINE_GATE_EVALUATED",
        payload=payload,
    )
    session.add(
        DecisionLog(
            ts=now,
            actor=ActorType.SYSTEM,
            module="pipeline",
            decision_type="PIPELINE_GATE_EVALUATED",
            payload=payload,
            prev_hash=prev_hash,
            hash=new_hash,
        )
    )

    if result.verdict == Verdict.KILL.value:
        session.add(
            Alert(
                ts=now,
                level=AlertLevel.CRITICA,
                module="pipeline",
                message=f"Candidato {candidate.bot_id} en KILL ({result.verdict_reason}).",
                action_required="Autopsia obligatoria antes de archivar en el Cementerio.",
            )
        )

    event = {
        "type": "pipeline.gate_evaluated",
        "ts": now.isoformat(),
        "candidate_id": candidate.id,
        "bot_id": candidate.bot_id,
        "verdict": result.verdict,
        "verdict_reason": result.verdict_reason,
        "gates_passed": result.gates_passed,
        "gates_total": result.gates_total,
        "provisional": result.provisional,
    }
    await redis.publish("events:pipeline", json.dumps(event))
