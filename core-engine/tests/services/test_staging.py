from datetime import UTC, datetime
from decimal import Decimal

import fakeredis

from core.db.enums import PipelinePhase, Verdict
from core.services.staging import (
    active_sizing_sum,
    compute_sizing_cap_breach,
    escalate_staging_step,
)
from core.state_machines.types import PipelineGateConfig, PipelineGateMetrics
from tests.factories import AccountFactory, BotFactory

CONFIG = PipelineGateConfig(staging_steps=(10, 25, 50, 100), sizing_total_cap=Decimal("89"))
PASSING_METRICS = PipelineGateMetrics(
    profit_factor=1.8,
    expectancy_r=0.25,
    sharpe=1.4,
    max_dd_pct=10.0,
    oos_trades=45,
    incubation_days=90,
    trades_per_week=3.0,
)


async def _account(db_session: object) -> object:
    account = AccountFactory()
    db_session.add(account)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    return account


class TestActiveSizingSum:
    async def test_sums_only_production_bots(self, db_session: object) -> None:
        account = await _account(db_session)
        db_session.add(  # type: ignore[attr-defined]
            BotFactory(
                account_id=account.id,
                pipeline_phase=PipelinePhase.F7,
                sizing_current_pct=Decimal("50.00"),
            )
        )
        db_session.add(  # type: ignore[attr-defined]
            BotFactory(
                account_id=account.id,
                pipeline_phase=PipelinePhase.F7,
                sizing_current_pct=Decimal("30.00"),
            )
        )
        db_session.add(  # type: ignore[attr-defined]
            BotFactory(
                account_id=account.id,
                pipeline_phase=PipelinePhase.F2,
                sizing_current_pct=Decimal("100.00"),
            )
        )
        await db_session.flush()  # type: ignore[attr-defined]

        total = await active_sizing_sum(db_session)  # type: ignore[arg-type]
        assert total == Decimal("80.00")


class TestComputeSizingCapBreach:
    async def test_breaches_when_sum_exceeds_cap(self, db_session: object) -> None:
        account = await _account(db_session)
        candidate_bot = BotFactory(
            account_id=account.id,
            pipeline_phase=PipelinePhase.F7,
            sizing_current_pct=Decimal("10.00"),
        )
        db_session.add(candidate_bot)  # type: ignore[attr-defined]
        db_session.add(  # type: ignore[attr-defined]
            BotFactory(
                account_id=account.id,
                pipeline_phase=PipelinePhase.F7,
                sizing_current_pct=Decimal("85.00"),
            )
        )
        await db_session.flush()  # type: ignore[attr-defined]

        breach = await compute_sizing_cap_breach(  # type: ignore[arg-type]
            db_session, candidate_bot.id, Decimal("10"), CONFIG
        )
        assert breach is True

    async def test_does_not_breach_when_within_cap(self, db_session: object) -> None:
        account = await _account(db_session)
        candidate_bot = BotFactory(
            account_id=account.id,
            pipeline_phase=PipelinePhase.F7,
            sizing_current_pct=Decimal("10.00"),
        )
        db_session.add(candidate_bot)  # type: ignore[attr-defined]
        db_session.add(  # type: ignore[attr-defined]
            BotFactory(
                account_id=account.id,
                pipeline_phase=PipelinePhase.F7,
                sizing_current_pct=Decimal("20.00"),
            )
        )
        await db_session.flush()  # type: ignore[attr-defined]

        breach = await compute_sizing_cap_breach(  # type: ignore[arg-type]
            db_session, candidate_bot.id, Decimal("10"), CONFIG
        )
        assert breach is False


class TestEscalateStagingStep:
    async def test_go_advances_bot_sizing_to_next_step(self, db_session: object) -> None:
        from core.db.models.pipeline import PipelineCandidate

        account = await _account(db_session)
        bot = BotFactory(
            account_id=account.id,
            pipeline_phase=PipelinePhase.F7,
            sizing_current_pct=Decimal("10.00"),
        )
        db_session.add(bot)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        candidate = PipelineCandidate(
            bot_id=bot.id,
            current_phase=PipelinePhase.F7,
            entered_phase_at=datetime.now(UTC),
            incubation_days=90,
            oos_trades=45,
        )
        db_session.add(candidate)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]

        redis = fakeredis.FakeAsyncRedis()
        now = datetime.now(UTC)
        result = await escalate_staging_step(  # type: ignore[arg-type]
            db_session, redis, candidate, PASSING_METRICS, CONFIG, now
        )
        await db_session.commit()  # type: ignore[attr-defined]

        assert result.verdict == Verdict.GO.value
        refreshed_bot = await db_session.get(type(bot), bot.id)  # type: ignore[attr-defined]
        assert refreshed_bot.sizing_current_pct == Decimal("25.00")
        await redis.aclose()

    async def test_sizing_cap_blocks_escalation_above_89_percent(self, db_session: object) -> None:
        from core.db.models.pipeline import PipelineCandidate

        account = await _account(db_session)
        bot = BotFactory(
            account_id=account.id,
            pipeline_phase=PipelinePhase.F7,
            sizing_current_pct=Decimal("50.00"),
        )
        db_session.add(bot)  # type: ignore[attr-defined]
        db_session.add(  # type: ignore[attr-defined]
            BotFactory(
                account_id=account.id,
                pipeline_phase=PipelinePhase.F7,
                sizing_current_pct=Decimal("60.00"),
            )
        )
        await db_session.flush()  # type: ignore[attr-defined]
        candidate = PipelineCandidate(
            bot_id=bot.id,
            current_phase=PipelinePhase.F7,
            entered_phase_at=datetime.now(UTC),
            incubation_days=90,
            oos_trades=45,
        )
        db_session.add(candidate)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]

        redis = fakeredis.FakeAsyncRedis()
        now = datetime.now(UTC)
        result = await escalate_staging_step(  # type: ignore[arg-type]
            db_session, redis, candidate, PASSING_METRICS, CONFIG, now
        )
        await db_session.commit()  # type: ignore[attr-defined]

        assert result.verdict == Verdict.HOLD.value
        assert result.verdict_reason == "SIZING_CAP"
        refreshed_bot = await db_session.get(type(bot), bot.id)  # type: ignore[attr-defined]
        assert refreshed_bot.sizing_current_pct == Decimal("50.00")
        await redis.aclose()
