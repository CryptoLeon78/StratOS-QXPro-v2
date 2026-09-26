from datetime import UTC, datetime, timedelta
from decimal import Decimal

import fakeredis

from core.db.enums import BotRole, PipelinePhase
from core.db.models.pipeline import PipelineCandidate
from core.services import f6_staging
from core.services.f6_staging import F6StagingOutcome, evaluate_f6_candidate
from core.services.incubation_observation import IncubationObservation
from core.state_machines.types import ChallengerConfig, PipelineGateConfig
from tests.factories import AccountFactory, BotFactory, IngestBatchFactory, TradeFactory


async def _f6_candidate(db_session: object, now: datetime) -> tuple[object, object, object, object]:
    account = AccountFactory()
    db_session.add(account)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    bot = BotFactory(
        account_id=account.id,
        role=BotRole.CHALLENGER,
        pipeline_phase=PipelinePhase.F6,
        sizing_current_pct=Decimal("0.20"),
    )
    db_session.add(bot)  # type: ignore[attr-defined]
    batch = IngestBatchFactory(account_id=account.id)
    db_session.add(batch)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    candidate = PipelineCandidate(
        bot_id=bot.id,
        current_phase=PipelinePhase.F6,
        entered_phase_at=now - timedelta(days=1),
        incubation_days=90,
        oos_trades=30,
    )
    db_session.add(candidate)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    return account, bot, candidate, batch


def _observation(candidate: object, bot: object) -> IncubationObservation:
    return IncubationObservation(
        candidate_id=candidate.id,  # type: ignore[attr-defined]
        bot_id=bot.id,  # type: ignore[attr-defined]
        magic_number=bot.magic_number,  # type: ignore[attr-defined]
        current_phase=PipelinePhase.F6,
        observation_started_at=candidate.entered_phase_at,  # type: ignore[attr-defined]
        tester_baseline=None,
        demo_trade_count=0,
        demo_trade_first_open_at=None,
        demo_trade_last_close_at=None,
        valid_observation_days=90,
        ea_state={"ea_version": "incubadora-reporter-v1.3"},
        latest_heartbeat_at=datetime.now(UTC),
        latest_equity=None,
        observation_status="OBSERVED",
        missing_evidence=(),
    )


async def test_initial_staging_plan_is_auditable_and_does_not_touch_f7_or_mt5_state(
    db_session: object, monkeypatch: object
) -> None:
    now = datetime(2026, 9, 10, tzinfo=UTC)
    _, bot, candidate, _ = await _f6_candidate(db_session, now)

    async def observed(_: object, item: object) -> IncubationObservation:
        return _observation(item, bot)

    monkeypatch.setattr(f6_staging, "assemble_incubation_observation", observed)  # type: ignore[attr-defined]
    redis = fakeredis.FakeAsyncRedis()
    result = await evaluate_f6_candidate(
        db_session,
        redis,
        candidate,
        PipelineGateConfig(),
        ChallengerConfig(),
        now,  # type: ignore[arg-type]
    )
    await db_session.flush()  # type: ignore[attr-defined]
    repeated = await evaluate_f6_candidate(
        db_session,
        redis,
        candidate,
        PipelineGateConfig(),
        ChallengerConfig(),
        now,  # type: ignore[arg-type]
    )

    assert result is not None and result.created is True
    assert result.evaluation.outcome == F6StagingOutcome.READY_FOR_OPERATOR_CONFIRMATION
    assert result.evaluation.requested_sizing_pct == Decimal("10")
    assert result.evaluation.challenger["status"] == "SLOT_UNDECLARED"
    assert bot.sizing_current_pct == Decimal("0.20")
    assert candidate.current_phase == PipelinePhase.F6
    assert bot.pipeline_phase == PipelinePhase.F6
    assert repeated is not None and repeated.created is False
    await redis.aclose()


async def test_staging_requires_new_f6_trades_before_the_second_step(
    db_session: object, monkeypatch: object
) -> None:
    now = datetime(2026, 9, 10, tzinfo=UTC)
    account, bot, candidate, batch = await _f6_candidate(db_session, now)
    bot.sizing_current_pct = Decimal("10")
    for index in range(19):
        db_session.add(  # type: ignore[attr-defined]
            TradeFactory(
                bot_id=bot.id,
                account_id=account.id,
                magic_number=bot.magic_number,
                open_time=now - timedelta(hours=index + 2),
                close_time=now - timedelta(hours=index + 1),
                profit=Decimal("1"),
                commission=Decimal("0"),
                swap=Decimal("0"),
                r_multiple=Decimal("1"),
                ingest_batch_id=batch.id,
            )
        )
    await db_session.flush()  # type: ignore[attr-defined]

    async def observed(_: object, item: object) -> IncubationObservation:
        return _observation(item, bot)

    monkeypatch.setattr(f6_staging, "assemble_incubation_observation", observed)  # type: ignore[attr-defined]
    redis = fakeredis.FakeAsyncRedis()
    result = await evaluate_f6_candidate(
        db_session,
        redis,
        candidate,
        PipelineGateConfig(),
        ChallengerConfig(),
        now,  # type: ignore[arg-type]
    )

    assert result is not None
    assert result.evaluation.outcome == F6StagingOutcome.HOLD
    assert result.evaluation.reason == "INSUFFICIENT_STAGING_TRADES"
    assert result.evaluation.requested_sizing_pct == Decimal("25")
    assert bot.sizing_current_pct == Decimal("10")
    assert candidate.current_phase == PipelinePhase.F6
    await redis.aclose()


async def test_sizing_cap_blocks_initial_f6_plan_without_phase_promotion(
    db_session: object, monkeypatch: object
) -> None:
    now = datetime(2026, 9, 10, tzinfo=UTC)
    account, bot, candidate, _ = await _f6_candidate(db_session, now)
    db_session.add(  # type: ignore[attr-defined]
        BotFactory(
            account_id=account.id,
            pipeline_phase=PipelinePhase.F7,
            sizing_current_pct=Decimal("85"),
        )
    )
    await db_session.flush()  # type: ignore[attr-defined]

    async def observed(_: object, item: object) -> IncubationObservation:
        return _observation(item, bot)

    monkeypatch.setattr(f6_staging, "assemble_incubation_observation", observed)  # type: ignore[attr-defined]
    redis = fakeredis.FakeAsyncRedis()
    result = await evaluate_f6_candidate(
        db_session,
        redis,
        candidate,
        PipelineGateConfig(),
        ChallengerConfig(),
        now,  # type: ignore[arg-type]
    )

    assert result is not None
    assert result.evaluation.outcome == F6StagingOutcome.SIZING_CAP
    assert result.evaluation.reason == "SIZING_CAP"
    assert candidate.current_phase == PipelinePhase.F6
    assert bot.pipeline_phase == PipelinePhase.F6
    await redis.aclose()
