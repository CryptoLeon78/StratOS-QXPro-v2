from datetime import UTC, datetime, timedelta
from decimal import Decimal

import fakeredis

from core.db.enums import PipelinePhase
from core.db.models.market import EquitySnapshot, HeartbeatLog
from core.db.models.pipeline import PipelineCandidate
from core.services import incubation_observation
from core.services.incubation_observation import (
    IncubationObservation,
    assemble_incubation_observation,
)
from tests.factories import AccountFactory, BotFactory, IngestBatchFactory, TradeFactory


async def test_observation_excludes_tester_trades_and_pre_f4_telemetry(db_session: object) -> None:
    now = datetime.now(UTC)
    account = AccountFactory()
    db_session.add(account)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    bot = BotFactory(account_id=account.id, pipeline_phase=PipelinePhase.F4)
    db_session.add(bot)  # type: ignore[attr-defined]
    batch = IngestBatchFactory(account_id=account.id)
    db_session.add(batch)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    candidate = PipelineCandidate(
        bot_id=bot.id,
        current_phase=PipelinePhase.F4,
        entered_phase_at=now,
        incubation_days=0,
        oos_trades=0,
    )
    db_session.add(candidate)  # type: ignore[attr-defined]
    db_session.add_all(  # type: ignore[attr-defined]
        [
            TradeFactory(
                bot_id=bot.id,
                account_id=account.id,
                magic_number=bot.magic_number,
                open_time=now - timedelta(minutes=1),
                close_time=now,
                ingest_batch_id=batch.id,
            ),
            HeartbeatLog(
                ts=now - timedelta(seconds=1),
                connector_instance_id="connector-test",
                account_id=account.id,
                latency_ms=1,
                status="OK",
            ),
            EquitySnapshot(
                ts=now - timedelta(seconds=1),
                account_id=account.id,
                equity=Decimal("100.00"),
                balance=Decimal("100.00"),
                drawdown_pct=Decimal("0.000"),
                margin_level=None,
                free_margin=None,
            ),
        ]
    )
    await db_session.flush()  # type: ignore[attr-defined]

    observation = await assemble_incubation_observation(db_session, candidate)  # type: ignore[arg-type]

    assert observation is not None
    assert observation.demo_trade_count == 0
    assert observation.valid_observation_days == 0
    assert "heartbeat" in observation.missing_evidence
    assert "equity" in observation.missing_evidence


async def test_observation_counts_only_days_with_both_demo_streams(db_session: object) -> None:
    start = datetime(2026, 9, 10, 10, tzinfo=UTC)
    account = AccountFactory()
    db_session.add(account)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    bot = BotFactory(account_id=account.id, pipeline_phase=PipelinePhase.F4)
    db_session.add(bot)  # type: ignore[attr-defined]
    batch = IngestBatchFactory(account_id=account.id)
    db_session.add(batch)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    candidate = PipelineCandidate(
        bot_id=bot.id,
        current_phase=PipelinePhase.F4,
        entered_phase_at=start,
        incubation_days=0,
        oos_trades=0,
    )
    db_session.add(candidate)  # type: ignore[attr-defined]
    db_session.add_all(  # type: ignore[attr-defined]
        [
            TradeFactory(
                bot_id=bot.id,
                account_id=account.id,
                magic_number=bot.magic_number,
                open_time=start + timedelta(hours=1),
                close_time=start + timedelta(hours=2),
                ingest_batch_id=batch.id,
            ),
            HeartbeatLog(
                ts=start + timedelta(hours=1),
                connector_instance_id="connector-test",
                account_id=account.id,
                latency_ms=1,
                status="OK",
            ),
            HeartbeatLog(
                ts=start + timedelta(days=1, hours=1),
                connector_instance_id="connector-test",
                account_id=account.id,
                latency_ms=1,
                status="OK",
            ),
            EquitySnapshot(
                ts=start + timedelta(hours=2),
                account_id=account.id,
                equity=Decimal("101.00"),
                balance=Decimal("101.00"),
                drawdown_pct=Decimal("0.000"),
                margin_level=None,
                free_margin=None,
            ),
        ]
    )
    await db_session.flush()  # type: ignore[attr-defined]

    observation = await assemble_incubation_observation(db_session, candidate)  # type: ignore[arg-type]

    assert observation is not None
    assert observation.demo_trade_count == 1
    assert observation.valid_observation_days == 1
    assert observation.demo_trade_first_open_at == start + timedelta(hours=1)
    assert "valid_observation_day" not in observation.missing_evidence


async def test_observed_f4_advances_only_through_system_transition(
    db_session: object, monkeypatch: object
) -> None:
    account = AccountFactory()
    db_session.add(account)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    bot = BotFactory(account_id=account.id, pipeline_phase=PipelinePhase.F4)
    db_session.add(bot)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    candidate = PipelineCandidate(
        bot_id=bot.id,
        current_phase=PipelinePhase.F4,
        entered_phase_at=datetime.now(UTC),
        incubation_days=0,
        oos_trades=0,
    )
    db_session.add(candidate)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]

    async def observed(_: object, item: PipelineCandidate) -> IncubationObservation:
        return IncubationObservation(
            candidate_id=item.id,
            bot_id=item.bot_id,
            magic_number=bot.magic_number,
            current_phase=PipelinePhase.F4,
            observation_started_at=item.entered_phase_at,
            tester_baseline=None,
            demo_trade_count=0,
            demo_trade_first_open_at=None,
            demo_trade_last_close_at=None,
            valid_observation_days=1,
            ea_state=None,
            latest_heartbeat_at=datetime.now(UTC),
            latest_equity=None,
            observation_status="OBSERVED",
            missing_evidence=(),
        )

    monkeypatch.setattr(incubation_observation, "assemble_incubation_observation", observed)  # type: ignore[attr-defined]
    redis = fakeredis.FakeAsyncRedis()
    advanced = await incubation_observation.advance_observed_f4_candidates(  # type: ignore[arg-type]
        db_session, redis, account
    )
    await db_session.flush()  # type: ignore[attr-defined]

    assert advanced == [candidate.id]
    assert candidate.current_phase == PipelinePhase.F5
    assert bot.pipeline_phase == PipelinePhase.F5
    await redis.aclose()
