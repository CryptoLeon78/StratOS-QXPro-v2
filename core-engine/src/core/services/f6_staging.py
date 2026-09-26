"""Evaluación F6 de escalado y challenger/champion, estrictamente read-only.

La evidencia de F5 habilita la entrada a F6. A partir de ahí este servicio
revalida cada escalón de staging y compara un challenger con el único
champion declarado para su mismo slot. Nunca invoca el agente MT5, nunca
modifica ``sizing_current_pct`` y nunca transiciona a F7.
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from statsmodels.stats.weightstats import ttest_ind

from core.db.enums import BotRole, CorrelationSource, PipelinePhase, Verdict
from core.db.models.accounts import Bot
from core.db.models.governance import CorrelationSnapshot, CorrelationSnapshotPair
from core.db.models.market import Trade
from core.db.models.pipeline import ChallengerEvaluation, F6StagingEvaluation, PipelineCandidate
from core.formulas.trading import expectancy_r, max_drawdown_pct, rolling_sharpe
from core.services.f6_evaluation import _metrics_from_rows
from core.services.incubation_observation import assemble_incubation_observation
from core.services.staging import compute_sizing_cap_breach
from core.state_machines.challenger import evaluate_challenger
from core.state_machines.pipeline import evaluate_pipeline_gate
from core.state_machines.types import ChallengerConfig, ChallengerMetrics, PipelineGateConfig

_BASE_EQUITY = Decimal("100")
_F6_PHASE = PipelinePhase.F6


class F6StagingOutcome(StrEnum):
    READY_FOR_OPERATOR_CONFIRMATION = "READY_FOR_OPERATOR_CONFIRMATION"
    HOLD = "HOLD"
    SIZING_CAP = "SIZING_CAP"
    MAXIMUM_REACHED = "MAXIMUM_REACHED"


@dataclass(frozen=True)
class F6StagingEvaluationResult:
    evaluation: F6StagingEvaluation
    created: bool


def _canonical_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def _config_snapshot(
    pipeline_config: PipelineGateConfig, challenger_config: ChallengerConfig
) -> tuple[dict[str, Any], str]:
    snapshot = {"pipeline": asdict(pipeline_config), "challenger": asdict(challenger_config)}
    return snapshot, _canonical_hash(snapshot)


def _next_step(current_pct: Decimal, steps: tuple[int, ...]) -> Decimal | None:
    for step in sorted(steps):
        decimal_step = Decimal(step)
        if decimal_step > current_pct:
            return decimal_step
    return None


async def _closed_trade_rows(
    session: AsyncSession, bot_id: int, since: datetime
) -> list[tuple[int, datetime, Decimal, Decimal, Decimal, Decimal | None]]:
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
                Trade.bot_id == bot_id,
                Trade.open_time >= since,
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


async def _single_champion(session: AsyncSession, slot: str) -> Bot | None:
    champions = list(
        (
            await session.scalars(
                select(Bot).where(
                    Bot.slot == slot,
                    Bot.role == BotRole.CHAMPION,
                    Bot.pipeline_phase.in_((PipelinePhase.F7, PipelinePhase.PRODUCCION)),
                )
            )
        ).all()
    )
    return champions[0] if len(champions) == 1 else None


async def _latest_block_correlations(
    session: AsyncSession, challenger_id: int, champion_id: int
) -> tuple[int, float, float] | None:
    """Return one common matrix window and average absolute block correlation.

    A negative correlation is still exposure to the same block for this
    contract, therefore the comparison is made on absolute correlations.
    Both bots must be present in the same latest matrix snapshot; otherwise
    the comparison stays fail-closed instead of mixing distinct windows.
    """
    snapshot = await session.scalar(
        select(CorrelationSnapshot)
        .where(
            CorrelationSnapshot.source == CorrelationSource.MT5_REAL,
            CorrelationSnapshot.status == "COMPLETED",
        )
        .order_by(CorrelationSnapshot.created_at.desc())
        .limit(1)
    )
    if snapshot is None:
        return None
    rows = list(
        (
            await session.scalars(
                select(CorrelationSnapshotPair).where(
                    CorrelationSnapshotPair.snapshot_id == snapshot.id
                )
            )
        ).all()
    )

    def values_for(bot_id: int) -> tuple[int, list[float]] | None:
        relevant = [row for row in rows if row.bot_a_id == bot_id or row.bot_b_id == bot_id]
        if not relevant:
            return None
        return snapshot.window_days, [abs(row.correlation) for row in relevant]

    challenger = values_for(challenger_id)
    champion = values_for(champion_id)
    if challenger is None or champion is None or challenger[0] != champion[0]:
        return None
    return (
        challenger[0],
        sum(challenger[1]) / len(challenger[1]),
        sum(champion[1]) / len(champion[1]),
    )


def _metric_summary(
    rows: list[tuple[int, datetime, Decimal, Decimal, Decimal, Decimal | None]],
) -> tuple[float, float, float, list[float]] | None:
    r_multiples = [float(value) for *_, value in rows if value is not None]
    if len(r_multiples) < 2:
        return None
    pnl = [profit + commission + swap for _, _, profit, commission, swap, _ in rows]
    equity = [_BASE_EQUITY]
    for value in pnl:
        equity.append(equity[-1] + value)
    return (
        rolling_sharpe(pnl, window=len(pnl)),
        float(max_drawdown_pct(equity)),
        expectancy_r([Decimal(str(value)) for value in r_multiples]),
        r_multiples,
    )


async def _challenger_payload(
    session: AsyncSession,
    candidate: PipelineCandidate,
    bot: Bot,
    challenger_config: ChallengerConfig,
    now: datetime,
) -> dict[str, Any]:
    """Evaluate only explicit, comparable evidence; do not infer a slot."""
    if bot.role != BotRole.CHALLENGER:
        return {"status": "NOT_A_CHALLENGER"}
    if not bot.slot:
        return {"status": "SLOT_UNDECLARED"}
    champion = await _single_champion(session, bot.slot)
    if champion is None:
        return {"status": "CHAMPION_UNAVAILABLE", "slot": bot.slot}
    correlations = await _latest_block_correlations(session, bot.id, champion.id)
    if correlations is None:
        return {
            "status": "CORRELATION_EVIDENCE_UNAVAILABLE",
            "slot": bot.slot,
            "champion_bot_id": champion.id,
        }
    window_days, challenger_corr, champion_corr = correlations
    window_start = now - timedelta(days=window_days)
    challenger_rows = await _closed_trade_rows(session, bot.id, window_start)
    champion_rows = await _closed_trade_rows(session, champion.id, window_start)
    challenger_summary = _metric_summary(challenger_rows)
    champion_summary = _metric_summary(champion_rows)
    if challenger_summary is None or champion_summary is None:
        return {
            "status": "COMPARABLE_R_MULTIPLES_UNAVAILABLE",
            "slot": bot.slot,
            "champion_bot_id": champion.id,
            "window_days": window_days,
        }
    challenger_sharpe, challenger_dd, challenger_exp, challenger_r = challenger_summary
    champion_sharpe, champion_dd, champion_exp, champion_r = champion_summary
    _, p_value, _ = ttest_ind(challenger_r, champion_r, alternative="larger", usevar="unequal")
    if p_value != p_value:
        return {
            "status": "SIGNIFICANCE_UNAVAILABLE",
            "slot": bot.slot,
            "champion_bot_id": champion.id,
            "window_days": window_days,
        }
    challenger_metrics = ChallengerMetrics(
        sharpe=challenger_sharpe,
        p_value=float(p_value),
        correlation_with_block=challenger_corr,
        max_dd_pct=challenger_dd,
        expectancy_r=challenger_exp,
    )
    champion_metrics = ChallengerMetrics(
        sharpe=champion_sharpe,
        p_value=float(p_value),
        correlation_with_block=champion_corr,
        max_dd_pct=champion_dd,
        expectancy_r=champion_exp,
    )
    result = evaluate_challenger(challenger_metrics, champion_metrics, challenger_config)
    return {
        "status": "EVALUATED",
        "slot": bot.slot,
        "champion_bot_id": champion.id,
        "window_days": window_days,
        "p_value": float(p_value),
        "criteria": result.criteria,
        "passed": result.passed,
    }


async def evaluate_f6_candidate(
    session: AsyncSession,
    redis: Redis,
    candidate: PipelineCandidate,
    pipeline_config: PipelineGateConfig,
    challenger_config: ChallengerConfig,
    now: datetime | None = None,
) -> F6StagingEvaluationResult | None:
    """Append a F6 plan. The Redis argument preserves the ingestion service
    interface; this evaluation deliberately publishes no execution command."""
    del redis
    if candidate.current_phase != _F6_PHASE:
        return None
    bot = await session.get(Bot, candidate.bot_id)
    if bot is None:
        raise ValueError(f"candidate {candidate.id} has no bot")
    evaluation_now = now or datetime.now(UTC)
    observation = await assemble_incubation_observation(session, candidate)
    if observation is None:
        return None
    rows = await _closed_trade_rows(session, bot.id, candidate.entered_phase_at)
    metrics = _metrics_from_rows(rows, observation.valid_observation_days, evaluation_now)
    config_snapshot, configuration_sha256 = _config_snapshot(pipeline_config, challenger_config)
    challenger = await _challenger_payload(
        session, candidate, bot, challenger_config, evaluation_now
    )
    next_step = _next_step(bot.sizing_current_pct, pipeline_config.staging_steps)
    evidence = {
        "candidate_id": candidate.id,
        "f6_started_at": candidate.entered_phase_at,
        "current_sizing_pct": bot.sizing_current_pct,
        "next_step": next_step,
        "observation_status": observation.observation_status,
        "valid_observation_days": observation.valid_observation_days,
        "trades": [(row[0], row[1], row[2], row[3], row[4], row[5]) for row in rows],
        "challenger": challenger,
        "config": config_snapshot,
    }
    evidence_sha256 = _canonical_hash(evidence)
    existing = await session.scalar(
        select(F6StagingEvaluation).where(
            F6StagingEvaluation.candidate_id == candidate.id,
            F6StagingEvaluation.evidence_sha256 == evidence_sha256,
        )
    )
    if existing is not None:
        return F6StagingEvaluationResult(evaluation=existing, created=False)

    gate = evaluate_pipeline_gate(metrics, pipeline_config)
    if next_step is None:
        outcome, reason, requested = F6StagingOutcome.MAXIMUM_REACHED, "MAXIMUM_STAGING_STEP", None
    elif bot.sizing_current_pct < Decimal(pipeline_config.staging_steps[0]):
        breach = await compute_sizing_cap_breach(session, bot.id, next_step, pipeline_config)
        outcome = (
            F6StagingOutcome.SIZING_CAP
            if breach
            else F6StagingOutcome.READY_FOR_OPERATOR_CONFIRMATION
        )
        reason = "SIZING_CAP" if breach else "INITIAL_STAGING_PLAN"
        requested = next_step
    elif metrics.oos_trades < pipeline_config.staging_min_trades:
        outcome, reason, requested = F6StagingOutcome.HOLD, "INSUFFICIENT_STAGING_TRADES", next_step
    else:
        breach = await compute_sizing_cap_breach(session, bot.id, next_step, pipeline_config)
        if breach:
            outcome, reason, requested = F6StagingOutcome.SIZING_CAP, "SIZING_CAP", next_step
        elif gate.verdict != Verdict.GO.value:
            # `verdict_reason` es opcional en el gate; sin ella el motivo queda
            # en el codigo generico en vez de propagar un None al registro.
            outcome = F6StagingOutcome.HOLD
            reason = gate.verdict_reason or "GATE_NOT_GO"
            requested = next_step
        else:
            outcome = F6StagingOutcome.READY_FOR_OPERATOR_CONFIRMATION
            reason = "STAGING_GATES_GO"
            requested = next_step
    evaluation = F6StagingEvaluation(
        candidate_id=candidate.id,
        evidence_sha256=evidence_sha256,
        configuration_sha256=configuration_sha256,
        outcome=outcome.value,
        reason=reason,
        requested_sizing_pct=requested,
        metrics={
            "profit_factor": metrics.profit_factor,
            "expectancy_r": metrics.expectancy_r,
            "sharpe": metrics.sharpe,
            "max_dd_pct": metrics.max_dd_pct,
            "oos_trades": metrics.oos_trades,
            "incubation_days": metrics.incubation_days,
            "trades_per_week": metrics.trades_per_week,
        },
        gates={
            "passed": gate.gates_passed,
            "total": gate.gates_total,
            "verdict": gate.verdict,
            "provisional": gate.provisional,
            "staging_min_trades": pipeline_config.staging_min_trades,
        },
        challenger=challenger,
        evaluated_at=evaluation_now,
    )
    session.add(evaluation)
    if challenger["status"] == "EVALUATED":
        session.add(
            ChallengerEvaluation(
                ts=evaluation_now,
                challenger_bot_id=bot.id,
                champion_bot_id=int(challenger["champion_bot_id"]),
                slot=str(challenger["slot"]),
                criteria=dict(challenger["criteria"]),
                passed=bool(challenger["passed"]),
                p_value=float(challenger["p_value"]),
                notes="F6 contractual comparison only; any F7 rotation remains a human decision.",
            )
        )
    await session.flush()
    return F6StagingEvaluationResult(evaluation=evaluation, created=True)


async def evaluate_f6_candidates_for_account(
    session: AsyncSession,
    redis: Redis,
    account_id: int,
    pipeline_config: PipelineGateConfig,
    challenger_config: ChallengerConfig,
) -> list[F6StagingEvaluationResult]:
    candidates = list(
        (
            await session.scalars(
                select(PipelineCandidate)
                .join(Bot, Bot.id == PipelineCandidate.bot_id)
                .where(
                    PipelineCandidate.current_phase == _F6_PHASE,
                    Bot.account_id == account_id,
                )
            )
        ).all()
    )
    results: list[F6StagingEvaluationResult] = []
    for candidate in candidates:
        result = await evaluate_f6_candidate(
            session, redis, candidate, pipeline_config, challenger_config
        )
        if result is not None:
            results.append(result)
    return results
