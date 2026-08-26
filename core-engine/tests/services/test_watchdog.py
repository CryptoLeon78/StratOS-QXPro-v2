import json
from datetime import UTC, datetime, timedelta

import fakeredis
from sqlalchemy import select

from core.db.enums import AlertLevel
from core.db.models.decisions import Alert
from core.formulas.types import WatchdogState
from core.services.watchdog import (
    WatchdogServiceConfig,
    check_vps_clock_drift,
    evaluate_all_bots,
    run_watchdog_sweep,
)
from tests.factories import (
    AccountFactory,
    BaselineFactory,
    BotFactory,
    IngestBatchFactory,
    TradeFactory,
)

CONFIG = WatchdogServiceConfig()


async def _account_and_bot(db_session: object, **bot_kwargs: object) -> tuple[object, object]:
    account = AccountFactory()
    db_session.add(account)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    bot = BotFactory(account_id=account.id, **bot_kwargs)
    db_session.add(bot)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    return account, bot


class TestEvaluateAllBots:
    async def test_bot_without_baseline_is_insufficient_data(self, db_session: object) -> None:
        _, bot = await _account_and_bot(db_session)
        now = datetime.now(UTC)
        rows = await evaluate_all_bots(db_session, CONFIG, now)  # type: ignore[arg-type]
        row = next(r for r in rows if r.bot_id == bot.id)
        assert row.state == WatchdogState.INSUFFICIENT_DATA

    async def test_bot_with_no_trades_is_dead(self, db_session: object) -> None:
        _, bot = await _account_and_bot(db_session)
        baseline = BaselineFactory(bot_id=bot.id, expected_trades_30d=10)
        db_session.add(baseline)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        bot.baseline_id = baseline.id  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]

        now = datetime.now(UTC)
        rows = await evaluate_all_bots(db_session, CONFIG, now)  # type: ignore[arg-type]
        row = next(r for r in rows if r.bot_id == bot.id)
        assert row.state == WatchdogState.DEAD
        assert row.observed_30d == 0
        assert row.expected_month == 10

    async def test_bot_trading_on_pace_is_ok(self, db_session: object) -> None:
        account, bot = await _account_and_bot(db_session)
        baseline = BaselineFactory(bot_id=bot.id, expected_trades_30d=2)
        db_session.add(baseline)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        bot.baseline_id = baseline.id  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]

        now = datetime.now(UTC)
        batch = IngestBatchFactory(account_id=account.id)
        db_session.add(batch)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        for i in range(2):
            db_session.add(  # type: ignore[attr-defined]
                TradeFactory(
                    bot_id=bot.id,
                    account_id=account.id,
                    magic_number=bot.magic_number,
                    open_time=now - timedelta(days=1 + i),
                    ingest_batch_id=batch.id,
                )
            )
        await db_session.flush()  # type: ignore[attr-defined]

        rows = await evaluate_all_bots(db_session, CONFIG, now)  # type: ignore[arg-type]
        row = next(r for r in rows if r.bot_id == bot.id)
        assert row.state == WatchdogState.OK
        assert row.observed_30d == 2


class TestRunWatchdogSweep:
    async def test_dead_bot_creates_critica_alert(self, db_session: object) -> None:
        _, bot = await _account_and_bot(db_session)
        baseline = BaselineFactory(bot_id=bot.id, expected_trades_30d=10)
        db_session.add(baseline)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        bot.baseline_id = baseline.id  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]

        redis = fakeredis.FakeAsyncRedis()
        pubsub = redis.pubsub()
        await pubsub.subscribe("events:alert")
        await pubsub.get_message(timeout=1)

        now = datetime.now(UTC)
        await run_watchdog_sweep(db_session, redis, CONFIG, now)  # type: ignore[arg-type]
        await db_session.commit()  # type: ignore[attr-defined]

        alert = (
            await db_session.execute(  # type: ignore[attr-defined]
                select(Alert).where(Alert.dedup_key == f"watchdog:{bot.id}")
            )
        ).scalar_one()
        assert alert.level == AlertLevel.CRITICA
        assert alert.resolved is False

        message = await pubsub.get_message(timeout=1)
        payload = json.loads(message["data"])
        assert payload["type"] == "alert.created"

        await pubsub.aclose()
        await redis.aclose()

    async def test_sweep_does_not_duplicate_alert_on_second_run(self, db_session: object) -> None:
        _, bot = await _account_and_bot(db_session)
        baseline = BaselineFactory(bot_id=bot.id, expected_trades_30d=10)
        db_session.add(baseline)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        bot.baseline_id = baseline.id  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]

        redis = fakeredis.FakeAsyncRedis()
        now = datetime.now(UTC)
        await run_watchdog_sweep(db_session, redis, CONFIG, now)  # type: ignore[arg-type]
        await run_watchdog_sweep(db_session, redis, CONFIG, now)  # type: ignore[arg-type]
        await db_session.commit()  # type: ignore[attr-defined]

        alerts = (
            (
                await db_session.execute(  # type: ignore[attr-defined]
                    select(Alert).where(Alert.dedup_key == f"watchdog:{bot.id}")
                )
            )
            .scalars()
            .all()
        )
        assert len(alerts) == 1
        await redis.aclose()

    async def test_recovered_bot_resolves_its_alert(self, db_session: object) -> None:
        account, bot = await _account_and_bot(db_session)
        baseline = BaselineFactory(bot_id=bot.id, expected_trades_30d=2)
        db_session.add(baseline)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        bot.baseline_id = baseline.id  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]

        redis = fakeredis.FakeAsyncRedis()
        now = datetime.now(UTC)
        await run_watchdog_sweep(db_session, redis, CONFIG, now)  # type: ignore[arg-type]
        await db_session.flush()  # type: ignore[attr-defined]

        batch = IngestBatchFactory(account_id=account.id)
        db_session.add(batch)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        for i in range(2):
            db_session.add(  # type: ignore[attr-defined]
                TradeFactory(
                    bot_id=bot.id,
                    account_id=account.id,
                    magic_number=bot.magic_number,
                    open_time=now - timedelta(days=1 + i),
                    ingest_batch_id=batch.id,
                )
            )
        await db_session.flush()  # type: ignore[attr-defined]
        await run_watchdog_sweep(db_session, redis, CONFIG, now)  # type: ignore[arg-type]
        await db_session.commit()  # type: ignore[attr-defined]

        alert = (
            await db_session.execute(  # type: ignore[attr-defined]
                select(Alert).where(Alert.dedup_key == f"watchdog:{bot.id}")
            )
        ).scalar_one()
        assert alert.resolved is True
        await redis.aclose()


class TestCheckVpsClockDrift:
    async def test_drift_above_threshold_creates_suave_alert(self, db_session: object) -> None:
        redis = fakeredis.FakeAsyncRedis()
        now = datetime.now(UTC)
        await check_vps_clock_drift(db_session, redis, drift_s=150, now=now)  # type: ignore[arg-type]
        await db_session.commit()  # type: ignore[attr-defined]

        alert = (
            await db_session.execute(  # type: ignore[attr-defined]
                select(Alert).where(Alert.dedup_key == "watchdog:vps_clock_drift")
            )
        ).scalar_one()
        assert alert.level == AlertLevel.SUAVE
        await redis.aclose()

    async def test_drift_within_threshold_creates_no_alert(self, db_session: object) -> None:
        redis = fakeredis.FakeAsyncRedis()
        now = datetime.now(UTC)
        await check_vps_clock_drift(db_session, redis, drift_s=50, now=now)  # type: ignore[arg-type]
        await db_session.commit()  # type: ignore[attr-defined]

        alerts = (
            (
                await db_session.execute(  # type: ignore[attr-defined]
                    select(Alert).where(Alert.dedup_key == "watchdog:vps_clock_drift")
                )
            )
            .scalars()
            .all()
        )
        assert alerts == []
        await redis.aclose()
