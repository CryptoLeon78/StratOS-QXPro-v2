from datetime import UTC, datetime, timedelta
from decimal import Decimal

import fakeredis
from sqlalchemy import func, select

from core.db.enums import PipelinePhase, Verdict
from core.db.models.pipeline import F6Evaluation, PipelineCandidate
from core.services import f6_evaluation
from core.services.f6_evaluation import F6Outcome, evaluate_f5_candidate
from core.services.incubation_observation import IncubationObservation
from core.state_machines.types import PipelineGateConfig
from tests.factories import AccountFactory, BotFactory, IngestBatchFactory, TradeFactory


async def _candidate(
    db_session: object, now: datetime
) -> tuple[object, object, PipelineCandidate, object]:
    account = AccountFactory()
    db_session.add(account)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    bot = BotFactory(account_id=account.id, pipeline_phase=PipelinePhase.F5)
    db_session.add(bot)  # type: ignore[attr-defined]
    batch = IngestBatchFactory(account_id=account.id)
    db_session.add(batch)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    candidate = PipelineCandidate(
        bot_id=bot.id,
        current_phase=PipelinePhase.F5,
        entered_phase_at=now - timedelta(days=90),
        incubation_days=0,
        oos_trades=0,
    )
    db_session.add(candidate)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    return account, bot, candidate, batch


def _observation(
    candidate: PipelineCandidate, bot: object, days: int = 90
) -> IncubationObservation:
    return IncubationObservation(
        candidate_id=candidate.id,
        bot_id=candidate.bot_id,
        magic_number=bot.magic_number,  # type: ignore[attr-defined]
        current_phase=PipelinePhase.F5,
        observation_started_at=candidate.entered_phase_at,
        tester_baseline=None,
        demo_trade_count=0,
        demo_trade_first_open_at=None,
        demo_trade_last_close_at=None,
        valid_observation_days=days,
        ea_state={"ea_version": "incubadora-reporter-v1.3"},
        latest_heartbeat_at=datetime.now(UTC),
        latest_equity=None,
        observation_status="OBSERVED",
        missing_evidence=(),
    )


async def _seed_closed_trades(
    db_session: object, account: object, bot: object, batch: object, now: datetime, profit: Decimal
) -> None:
    for index in range(30):
        close_time = now - timedelta(days=89 - index * 3)
        trade_profit = Decimal("-2.00") if profit > 0 and index % 5 == 0 else profit
        db_session.add(  # type: ignore[attr-defined]
            TradeFactory(
                bot_id=bot.id,  # type: ignore[attr-defined]
                account_id=account.id,  # type: ignore[attr-defined]
                magic_number=bot.magic_number,  # type: ignore[attr-defined]
                open_time=close_time - timedelta(hours=1),
                close_time=close_time,
                close_price=Decimal("1.1"),
                profit=trade_profit,
                commission=Decimal("0.00"),
                swap=Decimal("0.00"),
                r_multiple=Decimal("-0.50") if trade_profit < 0 else Decimal("1.00"),
                ingest_batch_id=batch.id,  # type: ignore[attr-defined]
            )
        )
    await db_session.flush()  # type: ignore[attr-defined]


async def test_insufficient_f5_evidence_is_postponed_without_phase_change(
    db_session: object, monkeypatch: object
) -> None:
    now = datetime(2026, 9, 10, tzinfo=UTC)
    _, bot, candidate, _ = await _candidate(db_session, now)

    async def observed(_: object, item: PipelineCandidate) -> IncubationObservation:
        return _observation(item, bot, days=1)

    monkeypatch.setattr(f6_evaluation, "assemble_incubation_observation", observed)  # type: ignore[attr-defined]
    redis = fakeredis.FakeAsyncRedis()
    result = await evaluate_f5_candidate(db_session, redis, candidate, PipelineGateConfig(), now)  # type: ignore[arg-type]
    await db_session.flush()  # type: ignore[attr-defined]
    repeated = await evaluate_f5_candidate(db_session, redis, candidate, PipelineGateConfig(), now)  # type: ignore[arg-type]

    assert result is not None
    assert repeated is not None and repeated.created is False
    assert result.evaluation.outcome == F6Outcome.POSTPONE
    assert candidate.current_phase == PipelinePhase.F5
    assert candidate.verdict == Verdict.HOLD
    assert candidate.verdict_reason == "INSUFFICIENT_SAMPLE_OR_TIME"
    await redis.aclose()


async def test_valid_f5_evidence_approves_only_to_f6(
    db_session: object, monkeypatch: object
) -> None:
    now = datetime(2026, 9, 10, tzinfo=UTC)
    account, bot, candidate, batch = await _candidate(db_session, now)
    await _seed_closed_trades(db_session, account, bot, batch, now, Decimal("10.00"))  # type: ignore[arg-type]

    async def observed(_: object, item: PipelineCandidate) -> IncubationObservation:
        return _observation(item, bot)

    monkeypatch.setattr(f6_evaluation, "assemble_incubation_observation", observed)  # type: ignore[attr-defined]
    redis = fakeredis.FakeAsyncRedis()
    first = await evaluate_f5_candidate(db_session, redis, candidate, PipelineGateConfig(), now)  # type: ignore[arg-type]
    await db_session.flush()  # type: ignore[attr-defined]
    second = await evaluate_f5_candidate(db_session, redis, candidate, PipelineGateConfig(), now)  # type: ignore[arg-type]

    assert first is not None and first.created is True
    assert first.evaluation.outcome == F6Outcome.APPROVE
    assert candidate.current_phase == PipelinePhase.F6
    assert bot.pipeline_phase == PipelinePhase.F6
    assert second is None
    count = await db_session.scalar(select(func.count()).select_from(F6Evaluation))  # type: ignore[attr-defined]
    assert count == 1
    await redis.aclose()


async def test_contractual_failure_rejects_but_does_not_archive_without_autopsy(
    db_session: object, monkeypatch: object
) -> None:
    now = datetime(2026, 9, 10, tzinfo=UTC)
    account, bot, candidate, batch = await _candidate(db_session, now)
    await _seed_closed_trades(db_session, account, bot, batch, now, Decimal("-10.00"))  # type: ignore[arg-type]

    async def observed(_: object, item: PipelineCandidate) -> IncubationObservation:
        return _observation(item, bot)

    monkeypatch.setattr(f6_evaluation, "assemble_incubation_observation", observed)  # type: ignore[attr-defined]
    redis = fakeredis.FakeAsyncRedis()
    result = await evaluate_f5_candidate(db_session, redis, candidate, PipelineGateConfig(), now)  # type: ignore[arg-type]
    await db_session.flush()  # type: ignore[attr-defined]

    assert result is not None
    assert result.evaluation.outcome == F6Outcome.REJECT
    assert candidate.current_phase == PipelinePhase.F5
    assert candidate.verdict == Verdict.KILL
    await redis.aclose()
