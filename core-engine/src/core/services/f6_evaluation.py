"""Evaluación contractual F6 a partir de evidencia F5 de Incubadora.

No abre MT5, no emite órdenes y nunca mezcla el baseline de Tester con los
trades demo. Una muestra todavía insuficiente se POSPONE en F5: no puede ser
un rechazo por el simple hecho de estar acumulando observación.
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.enums import ActorType, PipelinePhase, Verdict
from core.db.models.accounts import Bot
from core.db.models.market import Trade
from core.db.models.pipeline import F6Evaluation, PipelineCandidate
from core.formulas.pipeline import decision_eta_days, trades_per_week
from core.formulas.trading import (
    expectancy_r,
    max_drawdown_pct,
    rolling_profit_factor,
    rolling_sharpe,
)
from core.services.incubation_observation import (
    IncubationObservation,
    assemble_incubation_observation,
)
from core.services.pipeline_history import record_phase_transition
from core.state_machines.pipeline import apply_pipeline_gate, evaluate_pipeline_gate
from core.state_machines.types import GateResult, PipelineGateConfig, PipelineGateMetrics

_BASE_EQUITY = Decimal("100")
_F6_INPUT_PHASE = PipelinePhase.F5


class F6Outcome(StrEnum):
    APPROVE = "APPROVE"
    POSTPONE = "POSTPONE"
    REJECT = "REJECT"


@dataclass(frozen=True)
class F6EvaluationResult:
    evaluation: F6Evaluation
    created: bool


def _canonical_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def _config_snapshot(config: PipelineGateConfig) -> tuple[dict[str, Any], str]:
    snapshot = asdict(config)
    return snapshot, _canonical_hash(snapshot)


async def _f5_closed_trade_rows(
    session: AsyncSession, candidate: PipelineCandidate
) -> list[tuple[int, datetime, Decimal, Decimal, Decimal, Decimal | None]]:
    """Closed trades opened after F5 began; entries from Tester never qualify."""
    filas = (
        await session.execute(
            select(
                Trade.id,
                Trade.close_time,
                Trade.profit,
                Trade.commission,
                Trade.swap,
                Trade.r_multiple,
            )
            .where(
                Trade.bot_id == candidate.bot_id,
                Trade.open_time >= candidate.entered_phase_at,
                Trade.close_time.is_not(None),
            )
            .order_by(Trade.close_time.asc())
        )
    ).all()
    # `close_time.is_not(None)` ya lo garantiza en SQL, pero la columna es
    # nullable y el tipo estatico no refleja ese filtro. Se reafirma aqui en
    # vez de castear a ciegas: si alguna vez llegara un NULL, se descarta en
    # lugar de romper mas abajo con un tipo que no es el declarado.
    return [
        (trade_id, close_time, profit, commission, swap, r_multiple)
        for trade_id, close_time, profit, commission, swap, r_multiple in filas
        if close_time is not None
    ]


def _metrics_from_rows(
    rows: list[tuple[int, datetime, Decimal, Decimal, Decimal, Decimal | None]],
    observation_days: int,
    now: datetime,
) -> PipelineGateMetrics:
    net_profits = [profit + commission + swap for _, _, profit, commission, swap, _ in rows]
    close_times = [close_time for _, close_time, _, _, _, _ in rows]
    r_multiples = [r_multiple for _, _, _, _, _, r_multiple in rows if r_multiple is not None]
    equity_curve = [_BASE_EQUITY]
    for pnl in net_profits:
        equity_curve.append(equity_curve[-1] + pnl)
    # La frecuencia se calcula sobre los 30 días anteriores; la función pura
    # mantiene el ancho de ventana contractual fuera de esta capa de I/O.
    recent = [close_time for close_time in close_times if (now - close_time).days < 30]
    return PipelineGateMetrics(
        profit_factor=rolling_profit_factor(net_profits, window=len(net_profits)) or 0.0,
        expectancy_r=expectancy_r(r_multiples) if r_multiples else 0.0,
        sharpe=rolling_sharpe(net_profits, window=len(net_profits)),
        max_dd_pct=float(max_drawdown_pct(equity_curve)) if len(equity_curve) > 1 else 0.0,
        oos_trades=len(rows),
        incubation_days=observation_days,
        trades_per_week=trades_per_week(recent, window_days=30),
    )


def _metrics_payload(metrics: PipelineGateMetrics) -> dict[str, Any]:
    return {
        "profit_factor": metrics.profit_factor,
        "expectancy_r": metrics.expectancy_r,
        "sharpe": metrics.sharpe,
        "max_dd_pct": metrics.max_dd_pct,
        "oos_trades": metrics.oos_trades,
        "incubation_days": metrics.incubation_days,
        "trades_per_week": metrics.trades_per_week,
    }


def _postpone_result(
    metrics: PipelineGateMetrics, config: PipelineGateConfig, reason: str
) -> GateResult:
    candidate_result = evaluate_pipeline_gate(metrics, config)
    return GateResult(
        gates_passed=candidate_result.gates_passed,
        gates_total=candidate_result.gates_total,
        verdict=Verdict.HOLD.value,
        verdict_reason=reason,
        provisional=True,
    )


def _outcome_for(
    observation: IncubationObservation,
    metrics: PipelineGateMetrics,
    config: PipelineGateConfig,
) -> tuple[F6Outcome, GateResult]:
    if observation.observation_status != "OBSERVED":
        return F6Outcome.POSTPONE, _postpone_result(metrics, config, "OBSERVATION_INCOMPLETE")
    if metrics.oos_trades < config.min_trades or metrics.incubation_days < config.min_days:
        return F6Outcome.POSTPONE, _postpone_result(metrics, config, "INSUFFICIENT_SAMPLE_OR_TIME")
    gate = evaluate_pipeline_gate(metrics, config)
    if gate.verdict == Verdict.GO.value:
        return F6Outcome.APPROVE, gate
    if gate.verdict == Verdict.KILL.value:
        return F6Outcome.REJECT, gate
    return F6Outcome.POSTPONE, gate


def _evidence_payload(
    candidate: PipelineCandidate,
    observation: IncubationObservation,
    rows: list[tuple[int, datetime, Decimal, Decimal, Decimal, Decimal | None]],
    config_snapshot: dict[str, Any],
) -> dict[str, Any]:
    return {
        "candidate_id": candidate.id,
        "f5_started_at": candidate.entered_phase_at,
        "observation_status": observation.observation_status,
        "valid_observation_days": observation.valid_observation_days,
        "reporter_version": (
            None if observation.ea_state is None else observation.ea_state.get("ea_version")
        ),
        "trades": [
            {
                "id": trade_id,
                "close_time": close_time,
                "profit": profit,
                "commission": commission,
                "swap": swap,
                "r_multiple": r_multiple,
            }
            for trade_id, close_time, profit, commission, swap, r_multiple in rows
        ],
        "pipeline_gate_config": config_snapshot,
    }


async def evaluate_f5_candidate(
    session: AsyncSession,
    redis: Redis,
    candidate: PipelineCandidate,
    config: PipelineGateConfig,
    now: datetime | None = None,
) -> F6EvaluationResult | None:
    """Append one idempotent F6 decision for an F5 candidate.

    ``APPROVE`` advances only to F6 (staging record). ``REJECT`` retains the
    candidate in F5 because Cemetery requires a human autopsy; it never
    creates an MT5 action. ``POSTPONE`` retains F5 observation.
    """
    if candidate.current_phase != _F6_INPUT_PHASE:
        return None
    observation = await assemble_incubation_observation(session, candidate)
    if observation is None:
        return None
    evaluation_now = now or datetime.now(UTC)
    rows = await _f5_closed_trade_rows(session, candidate)
    metrics = _metrics_from_rows(rows, observation.valid_observation_days, evaluation_now)
    config_snapshot, configuration_sha256 = _config_snapshot(config)
    evidence_payload = _evidence_payload(candidate, observation, rows, config_snapshot)
    evidence_sha256 = _canonical_hash(evidence_payload)
    existing = await session.scalar(
        select(F6Evaluation).where(
            F6Evaluation.candidate_id == candidate.id,
            F6Evaluation.evidence_sha256 == evidence_sha256,
        )
    )
    if existing is not None:
        return F6EvaluationResult(evaluation=existing, created=False)

    outcome, gate = _outcome_for(observation, metrics, config)
    candidate.profit_factor = metrics.profit_factor
    candidate.expectancy_r = metrics.expectancy_r
    candidate.sharpe = metrics.sharpe
    candidate.max_dd_pct = Decimal(str(round(metrics.max_dd_pct, 4)))
    candidate.oos_trades = metrics.oos_trades
    candidate.trades_per_week = metrics.trades_per_week
    candidate.incubation_days = metrics.incubation_days
    candidate.decision_eta_days = decision_eta_days(
        metrics.oos_trades,
        config.min_trades,
        candidate.entered_phase_at,
        config.min_days,
        metrics.trades_per_week,
        evaluation_now,
    )
    await apply_pipeline_gate(session, redis, candidate, gate)

    evaluation = F6Evaluation(
        candidate_id=candidate.id,
        evidence_sha256=evidence_sha256,
        configuration_sha256=configuration_sha256,
        outcome=outcome.value,
        reason=gate.verdict_reason,
        metrics=_metrics_payload(metrics),
        gates={
            "passed": gate.gates_passed,
            "total": gate.gates_total,
            "verdict": gate.verdict,
            "provisional": gate.provisional,
            "observation_status": observation.observation_status,
            "missing_evidence": list(observation.missing_evidence),
        },
        evaluated_at=evaluation_now,
    )
    session.add(evaluation)
    if outcome == F6Outcome.APPROVE:
        bot = await session.get(Bot, candidate.bot_id)
        if bot is None:
            raise ValueError(f"candidate {candidate.id} has no bot")
        candidate.current_phase = PipelinePhase.F6
        candidate.entered_phase_at = evaluation_now
        bot.pipeline_phase = PipelinePhase.F6
        record_phase_transition(
            session,
            candidate,
            from_phase=PipelinePhase.F5,
            to_phase=PipelinePhase.F6,
            actor=ActorType.SYSTEM,
            reason="F6_APPROVED_AUTOMATIC",
        )
    await session.flush()
    return F6EvaluationResult(evaluation=evaluation, created=True)


async def evaluate_f5_candidates_for_account(
    session: AsyncSession,
    redis: Redis,
    account_id: int,
    config: PipelineGateConfig,
) -> list[F6EvaluationResult]:
    """Evaluate all F5 candidates affected by read-only account ingestion."""
    candidates = list(
        (
            await session.scalars(
                select(PipelineCandidate)
                .join(Bot, Bot.id == PipelineCandidate.bot_id)
                .where(
                    PipelineCandidate.current_phase == PipelinePhase.F5,
                    Bot.account_id == account_id,
                )
            )
        ).all()
    )
    results: list[F6EvaluationResult] = []
    for candidate in candidates:
        result = await evaluate_f5_candidate(session, redis, candidate, config)
        if result is not None:
            results.append(result)
    return results
