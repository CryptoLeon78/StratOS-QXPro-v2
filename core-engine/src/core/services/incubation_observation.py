"""Read-only F5 observation assembly for demo-incubation candidates.

Tester/baseline evidence and broker-demo observation are deliberately kept
separate.  A calendar day counts only when the demo account has both a sealed
heartbeat and an equity snapshot after the candidate entered F4/F5.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.enums import ActorType, PipelinePhase
from core.db.models.accounts import Account, Baseline, Bot
from core.db.models.market import EaState, EquitySnapshot, HeartbeatLog, Trade
from core.db.models.pipeline import PipelineCandidate
from core.services.demo_attachment import evaluate_demo_attachment
from core.services.pipeline_history import record_phase_transition

_OBSERVATION_PHASES = (PipelinePhase.F4, PipelinePhase.F5, PipelinePhase.F6, PipelinePhase.F7)


@dataclass(frozen=True)
class IncubationObservation:
    candidate_id: int
    bot_id: int
    magic_number: int
    current_phase: PipelinePhase
    observation_started_at: datetime
    tester_baseline: dict[str, object] | None
    demo_trade_count: int
    demo_trade_first_open_at: datetime | None
    demo_trade_last_close_at: datetime | None
    valid_observation_days: int
    ea_state: dict[str, object] | None
    latest_heartbeat_at: datetime | None
    latest_equity: dict[str, object] | None
    observation_status: str
    missing_evidence: tuple[str, ...]


async def assemble_incubation_observation(
    session: AsyncSession, candidate: PipelineCandidate
) -> IncubationObservation | None:
    """Build one F5 read model without changing candidate state or MT5."""
    if candidate.current_phase not in _OBSERVATION_PHASES:
        return None
    bot = await session.get(Bot, candidate.bot_id)
    if bot is None:
        return None
    state = await session.get(EaState, (bot.account_id, bot.magic_number))
    account = await session.get(Account, bot.account_id)
    if account is None:
        return None
    attachment = await evaluate_demo_attachment(session, candidate, bot, account)
    baseline = await session.get(Baseline, bot.baseline_id) if bot.baseline_id is not None else None
    start = candidate.entered_phase_at
    trades = list(
        (
            await session.execute(
                select(Trade.open_time, Trade.close_time)
                .where(Trade.bot_id == bot.id, Trade.open_time >= start)
                .order_by(Trade.open_time)
            )
        ).all()
    )
    heartbeat_times = list(
        (
            await session.scalars(
                select(HeartbeatLog.ts).where(
                    HeartbeatLog.account_id == bot.account_id, HeartbeatLog.ts >= start
                )
            )
        ).all()
    )
    equities = list(
        (
            await session.scalars(
                select(EquitySnapshot)
                .where(EquitySnapshot.account_id == bot.account_id, EquitySnapshot.ts >= start)
                .order_by(EquitySnapshot.ts)
            )
        ).all()
    )
    heartbeat_days = {timestamp.date() for timestamp in heartbeat_times}
    equity_days = {snapshot.ts.date() for snapshot in equities}
    valid_days = len(heartbeat_days & equity_days)
    missing: list[str] = []
    if not attachment.verified:
        missing.append("reporter_contract")
    if not heartbeat_times:
        missing.append("heartbeat")
    if not equities:
        missing.append("equity")
    if not valid_days:
        missing.append("valid_observation_day")
    status = "OBSERVED" if not missing else "WAITING_" + "_".join(item.upper() for item in missing)
    latest_equity = equities[-1] if equities else None
    return IncubationObservation(
        candidate_id=candidate.id,
        bot_id=bot.id,
        magic_number=bot.magic_number,
        current_phase=candidate.current_phase,
        observation_started_at=start,
        tester_baseline=None
        if baseline is None
        else {
            "profit_factor": baseline.profit_factor,
            "expectancy_r": baseline.expectancy_r,
            "sharpe": baseline.sharpe,
            "max_dd_pct": baseline.max_dd_pct,
            "created_at": baseline.created_at,
        },
        demo_trade_count=len(trades),
        demo_trade_first_open_at=trades[0][0] if trades else None,
        demo_trade_last_close_at=next(
            (close for _, close in reversed(trades) if close is not None), None
        ),
        valid_observation_days=valid_days,
        ea_state=None
        if state is None
        else {
            "mode": state.mode,
            "autotrading": state.autotrading,
            "ea_version": state.ea_version,
            "sizing_pct": state.sizing_pct,
            "last_ingested_at": state.last_ingested_at,
        },
        latest_heartbeat_at=max(heartbeat_times) if heartbeat_times else None,
        latest_equity=None
        if latest_equity is None
        else {
            "ts": latest_equity.ts,
            "equity": latest_equity.equity,
            "balance": latest_equity.balance,
            "drawdown_pct": latest_equity.drawdown_pct,
        },
        observation_status=status,
        missing_evidence=tuple(missing),
    )


async def advance_observed_f4_candidates(
    session: AsyncSession, redis: Redis, account: Account
) -> list[int]:
    """Advance F4 to F5 only after read-only demo observation is complete."""
    candidates = list(
        (
            await session.scalars(
                select(PipelineCandidate)
                .join(Bot, Bot.id == PipelineCandidate.bot_id)
                .where(
                    PipelineCandidate.current_phase == PipelinePhase.F4,
                    Bot.account_id == account.id,
                )
            )
        ).all()
    )
    advanced: list[int] = []
    for candidate in candidates:
        observation = await assemble_incubation_observation(session, candidate)
        if observation is None or observation.observation_status != "OBSERVED":
            continue
        bot = await session.get(Bot, candidate.bot_id)
        if bot is None:
            continue
        candidate.current_phase = PipelinePhase.F5
        candidate.entered_phase_at = datetime.now(UTC)
        bot.pipeline_phase = PipelinePhase.F5
        record_phase_transition(
            session,
            candidate,
            from_phase=PipelinePhase.F4,
            to_phase=PipelinePhase.F5,
            actor=ActorType.SYSTEM,
            reason="DEMO_OBSERVATION_STARTED",
        )
        await redis.publish(
            "events:pipeline",
            json.dumps(
                {
                    "type": "pipeline.incubation_observation_started",
                    "candidate_id": candidate.id,
                    "bot_id": candidate.bot_id,
                    "from_phase": PipelinePhase.F4.value,
                    "to_phase": PipelinePhase.F5.value,
                }
            ),
        )
        advanced.append(candidate.id)
    return advanced
